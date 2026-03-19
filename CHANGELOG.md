# Changelog

すべての注目すべき変更をこのファイルに記録します。本ファイルは「Keep a Changelog」の慣習に準拠しています。  
フォーマットは [日付付きのリリース] → 区分（Added / Changed / Fixed / Security 等）で記載します。

なお、本CHANGELOGはソースコード（src/ 以下）の実装内容から推測して作成しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回公開リリース。日本株の自動売買・データ収集・研究用ユーティリティ群を含むモジュール群を実装。

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - public API: data, strategy, execution, monitoring を想定。

- 環境設定管理（src/kabusys/config.py）
  - Settings クラスでアプリケーション設定を環境変数から取得。
  - 必須変数チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
  - デフォルト値: KABUSYS_ENV、LOG_LEVEL、KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH。
  - KABUSYS_ENV／LOG_LEVEL の妥当性検証（許容値チェック）。
  - 自動 .env 読み込み機能: プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local をロード。OS 環境変数を保護する protected ロジック、.env.local による上書きサポート。
  - .env パーサーは export 形式・クォート・エスケープ・行内コメント対応を実装。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- データ取得・保存（src/kabusys/data）
  - J-Quants API クライアント（jquants_client.py）
    - レートリミッター実装（120 req/min 固定間隔スロットリング）。
    - リトライ（指数バックオフ、最大 3 回）と 429/408/5xx ハンドリング。
    - 401 発生時のトークン自動リフレッシュ（1 回のみ、再帰防止）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT を利用した更新処理、fetched_at に UTC タイムスタンプ記録（Look-ahead bias 対策）。
    - 型変換ユーティリティ（_to_float, _to_int）を提供し不正データを安全に扱う。
  - ニュース収集（news_collector.py）
    - RSS フィードから記事収集 -> raw_news へ冪等保存。
    - URL 正規化（トラッキングパラメータ除去、ソート、スキーム/ホストの小文字化、フラグメント除去）。
    - 記事ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を保証。
    - defusedxml による XML パース、受信サイズ制限（MAX_RESPONSE_BYTES）、SSRF 対策を念頭にした URL 検証、バルク挿入のチャンク化。

- 研究・ファクター計算（src/kabusys/research）
  - ファクター計算モジュール（factor_research.py）
    - Momentum（mom_1m/mom_3m/mom_6m）、MA200 乖離（ma200_dev）の計算。
    - Volatility（20日ATR、atr_pct）、流動性（avg_turnover、volume_ratio）。
    - Value（per、roe） - raw_financials と prices_daily の組合せで算出。
    - DuckDB を用いた SQL ベースの実装で営業日欠損やウィンドウサイズ不足を考慮。
  - 特徴量探索・評価（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns: 任意ホライズン、デフォルト [1,5,21]）。
    - IC（Spearman のランク相関）計算（calc_ic）。
    - ファクター統計サマリー（factor_summary）と rank ユーティリティ。
  - research パッケージの公的な再エクスポートを提供。

- 戦略（src/kabusys/strategy）
  - 特徴量エンジニアリング（feature_engineering.py）
    - research の生ファクターを取り込み、ユニバースフィルタ（最低株価、平均売買代金）を適用。
    - 指定カラムの Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - 日付単位で features テーブルへ置換（トランザクション＋バルク挿入、冪等性確保）。
  - シグナル生成（signal_generator.py）
    - features と ai_scores を統合し、各コンポーネント（momentum/value/volatility/liquidity/news）を計算。
    - 重み（デフォルト配分）と閾値（デフォルト 0.60）による final_score 計算。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、サンプル閾値あり）で BUY 抑制。
    - エグジット（SELL）条件: ストップロス（-8%）およびスコア低下（threshold 未満）。SELL 優先で BUY から除外。
    - signals テーブルへの日付単位置換（トランザクションで原子性確保）。
  - strategy パッケージの公的再エクスポートを提供（build_features, generate_signals）。

- ロギングと診断
  - 各モジュールに詳細な logger 呼び出しを追加（info/debug/warning レベル）し、処理状況や例外時の情報を出力。

### Changed
- （初回リリースのため特段の「変更」はなし）

### Fixed
- .env パースの堅牢化
  - export プレフィックス対応、クォート内のエスケープ処理、行内コメント判定の厳格化により .env の多様な記法に対応。
- DuckDB 書き込み処理の安全性向上
  - features / signals 書き込みはトランザクションで DELETE→INSERT の置換を行い、例外時に ROLLBACK を試行して原子性を保証。
  - raw データ保存関数は PK 欠損行をスキップして警告ログを出力するようにし、部分的不整合を回避。
- HTTP クライアントの堅牢化
  - JSON デコード失敗時に詳細メッセージを出すように改善。
  - 429 応答時は Retry-After ヘッダを優先してリトライ間隔を決定。
  - ネットワーク系エラーでの再試行ロジックを明確化。

### Security
- news_collector で defusedxml を使用し XML 外部エンティティ攻撃等を防止。
- ニュース取得における URL 検証や受信サイズ制限で SSRF / メモリ DoS 攻撃緩和を実装。
- J-Quants クライアントでは Authorization ヘッダ管理とトークン自動更新のロジックを実装し、不正アクセスのリスクを低減。

### Notes / Known limitations
- signal_generator の一部のエグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等のカラムが必要。
- research および strategy の関数は DuckDB の prices_daily/raw_financials/features/ai_scores/positions/tables に依存。テーブルスキーマの準備が前提。
- news_collector の記事 ID は URL ベースのため、同一記事の URL 変動（例: パラメータ以外の差分）がある場合は重複扱いされる可能性あり。
- 一部の数値正規化（zscore_normalize）は kabusys.data.stats 側の実装に依存（本リリースでは再エクスポートあり）。

---

（本CHANGELOGはリポジトリのソースから推測して作成しています。実際のリリースノートとして利用する際は、リリース実績・コミット履歴を基に調整してください。）
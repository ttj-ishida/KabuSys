# Changelog

すべての重要な変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]
（次のリリースに向けた変更はここに記載します）

---

## [0.1.0] - 2026-03-20

初回公開リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。主要な追加点・設計方針は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ初期化: kabusys.__init__ にバージョン情報（0.1.0）と公開 API を定義。
  - モジュールエクスポート: strategy, execution, monitoring, data などを公開。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイル自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。テスト等で自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - 高機能な .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い）。
  - Settings クラスを提供し、必須環境変数の検査（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）、パス設定（duckdb/sqlite）や env/log_level の妥当性検査を実装。

- データ収集 / 永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限対応（120 req/min）。
    - 再試行（指数バックオフ）と HTTP ステータス条件によるリトライ制御（408/429/5xx 等を対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
    - ページネーションに対応した fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存 helper（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により重複を排除し、fetched_at を UTC ISO 形式で記録。
    - 型変換ユーティリティ (_to_float / _to_int) を実装し不正データに対する安全な取り扱いを実現。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードを収集して raw_news へ保存するための基礎実装を追加。
    - URL 正規化（トラッキングパラメータの除去、スキーム/ホスト小文字化、クエリのソート、フラグメント除去）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）などメモリ DoS 対策の定義。
    - defusedxml を用いた XML パース（XML Bomb 等への耐性）。
    - バルク INSERT のチャンク処理と重複排除方針（記事ID は正規化 URL のハッシュなどで一意化する設計）。

- 研究用ファクター計算（kabusys.research.factor_research）
  - ファクター群の実装:
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、MA200 乖離率（ウィンドウ内データ不足時は None）。
    - ボラティリティ/流動性（calc_volatility）: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率。
    - バリュー（calc_value）: latest 財務データとの組合せで PER / ROE を算出。
  - DuckDB 上の SQL とウィンドウ関数を活用した実装で外部 API に依存しない設計。

- 研究支援ユーティリティ（kabusys.research.feature_exploration）
  - 将来リターン計算（calc_forward_returns）: LEAD を用いて複数ホライズン（デフォルト: [1,5,21]）の将来リターンを算出。
  - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を計算。ties の平均ランク処理を行う rank ユーティリティを提供。
  - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出する統計サマリ関数。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を実装:
    - research モジュールで計算した生ファクターを取得し、ユニバースフィルタ（最低株価・最低流動性）を適用。
    - zscore_normalize を呼び出して正規化、±3 でクリップ。
    - target_date に対する日付単位の置換（削除→挿入、トランザクションで原子性保証）で features テーブルへ保存（冪等）。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を実装:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - sigmoid 変換、欠損成分は中立値 (0.5) で補完。
    - ユーザ指定 weights の検査・正規化（未知キーや非数値は除外、合計で再スケール）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数閾値に達する場合 BUY を抑制）。
    - BUY（threshold デフォルト 0.60）および SELL（ストップロス -8% / スコア低下）を生成。
    - positions / prices を参照したエグジット判定と signals テーブルへの日付単位の置換（冪等・トランザクション）。

- その他
  - strategy パッケージの公開 API に build_features / generate_signals を追加。
  - research パッケージに主要ユーティリティをエクスポート。

### Security
- news_collector で defusedxml を使用し XML パース時の安全性を考慮。
- ニュース取得時の受信サイズ上限を定義し大きなレスポンスによるメモリ問題を軽減。
- J-Quants クライアントでトークン周りの処理を明示的に扱い、不適切な再帰を防止（allow_refresh フラグ）。

### Design / Reliability
- DuckDB への書き込みは可能な限り冪等に設計（ON CONFLICT 等を活用）。
- features / signals の更新は日付単位で削除→挿入を行いトランザクションで原子性を確保。
- レート制御・リトライ・トークン自動更新等により外部 API 呼び出しの堅牢性を向上。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known limitations / TODO
- 一部設計（ニュース記事 ID のハッシュ生成・銘柄リンク付け、SSRF/IP アドレス検査など）の詳細実装は今後の拡張で完了予定（モジュール内にセキュリティ方針の定義あり）。
- signal_generator のトレーリングストップや時間決済などのエグジット条件は未実装（コメントで将来対応を示唆）。
- execution モジュールはパッケージに含まれるが実装は未追加（発注層の実装は別途検討）。

---

開発者向け補足:
- 環境変数関連の挙動は config.Settings を通じて取得してください。自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のテーブルスキーマに依存するため、初期化スクリプト（DDL）を用意してからデータ保存/集計を実行してください。
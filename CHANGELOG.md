# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」準拠です。  

## [0.1.0] - 2026-03-19

初回リリース。

### 追加
- パッケージ基盤
  - パッケージ初期化とバージョン管理を導入（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - パッケージ公開 API を定義（data, strategy, execution, monitoring を __all__ に含む）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装（パッケージ配布後も動作）。
  - .env パーサを実装（コメント行、export 形式、シングル/ダブルクォート、エスケープ、インラインコメント考慮）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - settings オブジェクトを通じた型付きアクセサ（J-Quants / kabu / Slack / DB パス / 環境判定 / ログレベル等）。
  - env 値・LOG_LEVEL のバリデーション（許容値チェック）。

- Data レイヤ（src/kabusys/data/）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - 再試行（指数バックオフ、最大3回）と特定の HTTP ステータス (408, 429, 5xx) に対するリトライロジックを導入。
    - 401 Unauthorized を検知した場合の自動トークンリフレッシュ（1回のみ）をサポート。
    - ページネーション対応のデータ取得（株価日足 / 財務 / カレンダー）。
    - DuckDB への冪等保存関数を提供（raw_prices, raw_financials, market_calendar）。ON CONFLICT / DO UPDATE を使用。
    - 型安全なパースユーティリティ（_to_float, _to_int）を実装。
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード収集、テキスト前処理、正規化された記事 ID（URL 正規化後の SHA-256）での冪等保存。
    - defusedxml を利用して XML 関連の脆弱性を軽減。
    - URL 正規化（トラッキングパラメータ除去、スキーム・ホスト小文字化、フラグメント除去、クエリソート）。
    - レスポンスサイズ制限（デフォルト 10MB）、SSRF・不正スキーム対策、バルク挿入のチャンク化などを考慮。
    - デフォルト RSS ソースとして Yahoo Finance を含む。

- Research レイヤ（src/kabusys/research/）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日移動平均乖離）、Volatility（20日 ATR / atr_pct、平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装。
    - 欠損や不足データの扱い（ウィンドウ不足時に None を返す）を明示。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：複数ホライズン対応、単一クエリで取得する実装。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関（ties の扱いを含む）を実装。
    - ファクター統計サマリー（factor_summary）とランク付けユーティリティ（rank）。
  - research パッケージの公開 API を整理。

- Strategy レイヤ（src/kabusys/strategy/）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research モジュールで計算した生ファクターをマージし、ユニバースフィルタ（最低株価・平均売買代金）を適用して正規化（z-score）を行う build_features を実装。
    - Z スコアを ±3 でクリップし、features テーブルへ日付単位で置換（トランザクションによる原子性確保）。
    - ルックアヘッドバイアス防止の設計（target_date 時点のデータのみ使用）。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付け合算により final_score を算出。
    - デフォルト重み、閾値（BUY=0.60）を採用。ユーザ重みは妥当性検査と再スケーリングを行う。
    - Bear レジーム判定（AI の regime_score の平均が負で一定サンプル数以上）により BUY を抑制。
    - エグジット判定（ストップロス -8% など）を実装し SELL シグナルを生成。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。
    - 欠損コンポーネントは中立値（0.5）で補完する方針を採用。

- DB / トランザクション設計
  - build_features / generate_signals / save_* 系関数は、日付単位の置換アップサートを行い、トランザクションや ON CONFLICT を用いて冪等性と原子性を担保。

### 変更
- （初回リリースのため履歴上の変更はありません）

### 既知の制限・未実装（ドキュメントとして明記）
- シグナルの一部エグジット条件は未実装（トレーリングストップや時間決済は positions テーブルに peak_price / entry_date 等の追加が必要）。
- research / strategy は外部発注 API（execution 層）には依存しない設計。発注処理は別層で実装予定。
- news_collector の記事→銘柄紐付け（news_symbols）などの一部運用的処理は実装想定だが、収集・保存のコア部分に注力している。

### セキュリティ関連
- RSS パースに defusedxml を利用し、XML Bomb 等の脆弱性軽減を行っている。
- ニュース収集時の URL 正規化・トラッキングパラメータ除去・スキーム検査により SSRF 等のリスクを低減している。
- J-Quants クライアントはトークンの自動リフレッシュやネットワーク障害時のリトライを備え、堅牢性を向上。

### 依存・設計方針
- DuckDB を主要なデータ格納・解析基盤として使用（SQL と Python の組合せで計算）。
- pandas 等の外部解析ライブラリに依存しない設計を心がけている（research モジュールも標準ライブラリ + DuckDB）。
- ルックアヘッドバイアス回避を重視し、target_date 時点で「システムが知り得る」データのみを使用する方針。

---

今後の予定（未リリース）
- execution 層の実装（kabu API / 注文処理の具現化）。
- monitoring パッケージの実装（Slack 通知 / メトリクス集計）。
- news⇄銘柄マッピングの自動化（NLP を用いたシンボル抽出）および追加の異常検出ロジック。
# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

- リリース履歴は逆順（新しいものが上）で記載します。
- 未公開の変更は Unreleased セクションに記載してください（現時点ではなし）。

## [0.1.0] - 2026-03-18

初回公開リリース。以下の主要コンポーネントと機能を実装しました。

### 追加 (Added)
- パッケージのエントリポイント
  - kabusys パッケージを追加。バージョン __version__ = "0.1.0" を定義し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で公開。

- 環境・設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込むユーティリティを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により、カレントディレクトリに依存しない自動ロードを実現。
  - .env/.env.local の読み込み順制御、既存 OS 環境の保護機能（protected set）、および KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 環境変数パースの堅牢化（コメント、クォート、export 形式対応、インラインコメント処理など）。
  - 必須設定取得メソッド（_require）と Settings クラスを追加（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、実行環境選択、ログレベル等）。
  - env/log_level の妥当性検査（許容値チェック）と is_live/is_paper/is_dev ユーティリティを提供。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを追加。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 の Retry-After 処理。
    - 401 受信時にリフレッシュトークンで自動的に ID トークンを更新して再試行する機構（無限再帰防止）。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT DO UPDATE）。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias 対策を想定。
    - 入力値変換ユーティリティ（_to_float, _to_int）で堅牢な型変換を行う。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからのニュース収集・前処理のためのモジュールを実装。
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。
    - レスポンス上限（10 MB）や gzip 解凍の上限チェック、受信サイズ超過の検出。
    - defusedxml を利用した安全な XML パース。
    - SSRF 対策:
      - リダイレクト先のスキーム検証・プライベートアドレス検出（DNS 解決して A/AAAA をチェック）。
      - リクエスト時の最終 URL 再検証。
      - スキームは http/https のみ許可。
    - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、クエリソート、フラグメント除去）と記事ID生成（正規化 URL の SHA-256 先頭 32 文字）。
    - テキスト前処理（URL 除去、空白正規化）。
    - 銘柄コード抽出ユーティリティ（4 桁数字パターン、known_codes に基づくフィルタ）。
    - raw_news / news_symbols への冪等保存（INSERT ... ON CONFLICT DO NOTHING、INSERT ... RETURNING を使用）およびトランザクション単位のチャンク挿入。
    - run_news_collection により複数ソースの収集と銘柄紐付けを統合。

- データ処理・特徴量 (kabusys.research)
  - feature_exploration モジュール
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1, 5, 21 営業日）先の将来リターンを一括で取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（欠損・非有限値を除外、少数レコードは None を返す）。
    - rank / factor_summary: 平均ランク（同順位は平均ランク）などを扱うユーティリティと基本統計量計算。
  - factor_research モジュール
    - calc_momentum: mom_1m/mom_3m/mom_6m、200 日移動平均乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range の NULL 伝播制御により過大評価を防止。
    - calc_value: raw_financials から最新の財務データを取得し PER/ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB のウィンドウ関数を活用し、日ベースのスキャン範囲にバッファを持たせる設計（週末・祝日を吸収）。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の DDL を導入（raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義のベースを追加）。
  - Raw / Processed / Feature / Execution 層に沿った設計文書に基づくスキーマを用意。

### 変更 (Changed)
- 初回リリースのため該当なし（新規実装）。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- XML パースに defusedxml を使用し XML Bomb 等の脆弱性に対応。
- RSS フェッチにおいて SSRF 対策を実装（リダイレクト時の先検証、プライベートアドレス拒否、スキーム制限）。
- ニュース収集におけるレスポンスサイズ制限（MAX_RESPONSE_BYTES）と gzip 解凍後チェックによりメモリ DoS を緩和。
- URL 正規化によりトラッキングパラメータを除去（プライバシー/冪等性向上）。

### 注意事項 / 既知の制約 (Notes)
- research モジュールは DuckDB の prices_daily / raw_financials テーブルのみを参照し、本番の発注 API や外部システムにはアクセスしない設計です（安全にオフライン解析可能）。
- fetch_* 関数はネットワークエラーや API 側の仕様変更に依存するため、実運用では追加の監視・リトライ設定（ログ出力・アラート）を推奨します。
- .env 自動読み込みはプロジェクトルートの検出に依存します。配布パッケージ環境やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector の銘柄抽出はシンプルな 4 桁数字マッチ（known_codes フィルタ）に依存します。誤抽出/見逃しが発生する可能性があるため、用途に応じて改善を検討してください。

---

今後の予定（例）
- strategy / execution / monitoring の具体的な実装（発注ロジック、ポジション管理、監視アラート）の追加。
- ニュースの自然言語処理（キーワード抽出、エンティティ抽出）やより高度な銘柄リンク付け。
- 単体テスト・統合テストの拡充および CI パイプライン構築。

--- 

（注）この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のプロジェクト方針や設計書と差分がある場合があります。必要であれば日付や細部を調整して下さい。
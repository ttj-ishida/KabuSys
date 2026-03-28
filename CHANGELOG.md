# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

## [0.1.0] - 2026-03-28

### 追加
- 基本パッケージ初期リリース: kabusys
  - パッケージバージョンを src/kabusys/__init__.py にて "0.1.0" として公開。
  - 公開サブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ によるエクスポート）。

- 環境設定管理モジュール (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組み（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）と、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読込無効化をサポート。
  - シンプルかつ堅牢な .env パーサ（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 必須設定取得用の _require と Settings クラスを提供。設定項目例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL の検証
  - 環境変数保護（既存 OS 環境変数を上書きしない / .env.local で上書き可）を実装。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理、営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar がない場合は曜日ベースのフォールバック（週末非営業日扱い）。
    - カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants API からの差分取得 → 冪等保存を行う。
    - 最大探索日数やバックフィル、健全性チェックなどの保護ロジックを導入。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質チェック結果・エラー集計を含む）。
    - 差分更新・バックフィル・品質チェックを想定した設計（idempotent 保存、品質問題は収集して呼び出し元に委ねる）。
    - DuckDB を用いた最大日付取得やテーブル存在チェックなどのユーティリティ関数。

- AI モジュール（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を使い、指定ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）内のニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメント評価。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1銘柄あたり記事数/文字数制限（10 件 / 3000 文字）によるトークン肥大化対策。
    - JSON Mode を想定したレスポンス検証ロジック（部分的に余分なテキストが混入する場合の復元含む）、スコア ±1.0 のクリップ。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、API 失敗時は該当チャンクをスキップ（フェイルセーフ）。
    - スコア取得後は ai_scores テーブルへ冪等置換（該当コードのみ DELETE → INSERT）して部分失敗時の既存データ保護。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（モジュール内 _call_openai_api を patch）。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と news_nlp によるマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - ma200_ratio の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュース抽出はタイトルのマクロキーワードでフィルタ。最大 20 件まで。
    - OpenAI 呼び出しに対するリトライ/フォールバック（API 全滅時は macro_sentiment = 0.0）を実装。
    - レジーム合成、閾値設定、ログ出力を実装。
    - API キー注入可能（引数 or OPENAI_API_KEY 環境変数）。

- リサーチモジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER / ROE）の計算関数を提供。
    - DuckDB を用いた SQL ベース実装で prices_daily / raw_financials を参照。欠損やデータ不足時の None 取り扱いを明確化。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（スピアマンランク相関）、ランク変換ユーティリティ（rank）。
    - ファクター統計サマリー（count, mean, std, min, max, median）。
    - pandas 等外部依存に頼らない純標準ライブラリ実装。

- その他ユーティリティ
  - data.etl から ETLResult を再エクスポート。
  - research パッケージから有用関数をまとめてエクスポート（zscore_normalize を含む）。

### 設計上の注記 / 既知の振る舞い
- ルックアヘッドバイアス対策:
  - 多くのスコアリング/判定関数内で datetime.today() / date.today() を直接参照せず、必ず target_date を明示的に受け取る設計。
  - DB クエリは target_date 未満や BETWEEN 範囲を用いて未来データを使わないようになっている。
- フェイルセーフとロバスト性:
  - OpenAI 呼び出しや外部 API 呼び出しの失敗は例外で即停止ではなく、ログ出力してフォールバック動作（スコア=0.0 など）で継続することを多くの箇所で採用。
  - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に行い、失敗時は ROLLBACK を試行。
- テスト容易性:
  - OpenAI 呼び出し箇所は内部関数をモック可能に実装（unittest.mock.patch を想定）。
  - 設定読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト時に自動ロードを抑止可能。
- デフォルトとハードコードされたパラメータ:
  - OpenAI モデル: gpt-4o-mini（news_nlp / regime_detector）
  - news_nlp バッチサイズ 20、スコアクリップ ±1.0、記事文字数上限 3000、記事数上限 10
  - regime_detector: MA 重み 0.7、マクロ重み 0.3、MA スケール 10、閾値（bull/bear）0.2
  - リトライ上限やバックオフ設定は各モジュールで定義（例: _MAX_RETRIES = 3, _RETRY_BASE_SECONDS = 1.0）
- DB: DuckDB を主要な分析用 DB として利用。SQLite（monitoring 用）にも対応する設定を提供。

### 変更点（初回リリースにつき該当なし）
- なし

### 修正（初回リリースにつき該当なし）
- なし

### セキュリティ（初回リリースにつき該当なし）
- なし

---

注: 本 CHANGELOG はソースコードの実装とコメントから推測して作成した初回リリース向けの要約です。実際のリリースノート作成時にはリリース手順やパッケージ配布に合わせて日付・項目を調整してください。
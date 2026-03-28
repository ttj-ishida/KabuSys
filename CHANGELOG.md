# CHANGELOG

すべての重要な変更点をここで管理します。本ファイルは "Keep a Changelog" の慣例に準拠しています。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買プラットフォームの基礎機能を実装しました。主に以下のモジュールと機能を含みます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開サブパッケージ: data, strategy, execution, monitoring。

- 環境設定管理 (`kabusys.config`)
  - .env ファイル（.env, .env.local）と OS 環境変数から設定を自動読み込みする仕組みを実装。プロジェクトルートは .git または pyproject.toml を起点に探索。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱いなどに対応）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、アプリ設定（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等）をプロパティ経由で取得。環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。
  - デフォルト値: KABUSYS_API_BASE_URL、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）等。

- ニュース NLP / AI 周り (`kabusys.ai`)
  - score_news（news_nlp）: raw_news と news_symbols を集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（ai_score）を計算、ai_scores テーブルへ冪等的に書き込む。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ実装（calc_news_window）。
    - バッチ処理（最大 20 銘柄／リクエスト）、1 銘柄あたり記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しは JSON mode を利用し、レスポンスの堅牢なパース/バリデーション実装（余計な前後テキストの復元処理含む）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - スコアは ±1.0 にクリップ。DuckDB の executemany に関する制約を考慮し、書き込み前に空リスト回避の処理を追加。
    - テスト容易性のため _call_openai_api をモジュール内に定義し patch による差し替えを想定。

  - score_regime（regime_detector）: ETF 1321（日経225連動型）の 200 日移動平均乖離（70%）とマクロニュース由来の LLM センチメント（30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む。
    - ma200_ratio 計算、マクロニュース抽出（キーワードベース）、OpenAI でのセンチメント評価、重み合成、閾値判定を実装。
    - API の失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
    - テスト容易性のため API 呼び出し関数を差し替え可能にしている。

- データ基盤 (`kabusys.data`)
  - calendar_management: JPX カレンダー管理関連ユーティリティを実装。
    - market_calendar を参照した営業日判定（is_trading_day）、前後営業日取得（next_trading_day, prev_trading_day）、期間内営業日取得（get_trading_days）、SQ 判定（is_sq_day）を提供。
    - カレンダーデータ未取得時は曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存する夜間バッチ処理を実装。バックフィル、最終取得日の健全性チェックをサポート。
  - pipeline / etl:
    - ETLResult データクラスを実装（取得・保存件数、品質問題、エラー集約など）。to_dict による出力整形をサポート。
    - 差分取得・バックフィル・品質チェックのためのユーティリティ関数（_get_max_date 等）を実装。
  - jquants_client と quality モジュールを利用する設計（外部 API 呼び出しは抽象化）。

- リサーチ (研究用) (`kabusys.research`)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離等を DuckDB SQL ベースで計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials を用いた PER・ROE 計算（最新の report_date を銘柄ごとに取得）。
    - 設計方針として DuckDB と SQL を基本とし、本番口座や発注 API にはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証を実施。
    - calc_ic: スピアマンランク相関（IC）を実装（ランクは平均ランクで ties を扱う）。
    - rank, factor_summary: ランク変換、各カラムの基本統計量（count/mean/std/min/max/median）を計算。
  - すべて標準ライブラリと DuckDB のみで構築。pandas 等に依存しない実装。

### 変更点（設計上の重要事項 / デフォルト挙動）
- 「未来参照（ルックアヘッド）バイアス防止」を徹底:
  - 各 AI/集計処理（score_news, score_regime 等）は date 引数を受け取り、datetime.today()/date.today() を直接参照しない設計。
  - DB クエリには target_date 未満や排他条件を明示して未来データを参照しない。

- 冪等性と部分失敗耐性:
  - ai_scores / market_regime 等への書き込みは既存レコードを絞って置換することで、部分失敗時に他データを保護。
  - DuckDB の executemany に関する制約（空リスト不可）に対応している。

- OpenAI 統合の堅牢化:
  - JSON mode のレスポンスに対する冗長テキスト耐性（最外の {} を抽出して復元）。
  - リトライ（429/ネットワーク/タイムアウト/5xx）と段階的バックオフ。
  - 重要な箇所でのフェイルセーフ（API 失敗時はスコア 0.0 にフォールバック、例外を上位に伝播させない箇所あり）。

- テスト性向上:
  - _call_openai_api などをモジュール内で定義し、unit test で patch しやすい設計。

### 修正・既知の注意点 (Fixed / Known issues)
- .env 読み込みでファイルアクセスに失敗した場合は warnings.warn で通知して続行するようにし、プロセスを停止させない挙動に変更。
- DuckDB 絡みの操作で executemany に空リストを渡すと失敗するため、事前に空チェックを挿入して回避。
- OpenAI API のエラー処理で status_code が存在しない場合にも安全に扱うため getattr を使用。

### セキュリティ / エラー
- OpenAI API キー（OPENAI_API_KEY）が未設定の場合、score_news / score_regime は ValueError を送出して明示的に失敗するように実装（API キーの必須化）。
- 環境変数読み込みで OS 環境を保護するため、.env 読み込み時に既存の OS 環境変数を保護する仕組みを導入（protected set）。

### 開発者向けメモ
- 自動 .env 読み込みを無効にしたいテストや CI 環境では、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分は unittest.mock.patch で簡単にモック化できます（kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api を差し替え）。
- DuckDB を用いるためスキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）の整備が前提です。

---

今後のリリースでは以下を想定しています（未実装／検討事項）
- strategy / execution / monitoring の具体的戦略・注文実行・監視コンポーネントの実装・統合。
- PBR・配当利回り等のバリュー指標追加、さらに詳しい品質チェックの強化。
- OpenAI 呼び出しのコスト最適化（圧縮プロンプト、キャッシュ等）。
- より詳細なテストカバレッジと CI ワークフローの整備。
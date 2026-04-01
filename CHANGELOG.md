# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記述しています。  
このファイルはリポジトリ内のコードから推測した初回リリースの変更履歴です。

全般的な方針:
- 日次バッチ、ETL、研究（リサーチ）・指標算出、AI を用いたニュースセンチメント、マーケットカレンダー管理など、日本株自動売買プラットフォーム向けの機能群を提供します。
- ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を直接参照しない設計が多用されています。
- OpenAI 呼び出しに対する再試行（エクスポネンシャルバックオフ）、フェイルセーフ（失敗時は中立スコア等）や、DuckDB への冪等書き込みパターンを採用しています。

## [Unreleased]

## [0.1.0] - 2026-04-01

### 追加 (Added)
- 基本パッケージ:
  - kabusys パッケージ初期化とバージョン管理を追加（__version__ = 0.1.0）。
  - パッケージの公開サブパッケージ一覧を __all__ に定義。

- 設定・環境変数管理:
  - .env ファイルおよび OS 環境変数から設定を読み込む settings モジュールを追加（kabusys.config.Settings）。
  - 自動 .env 読み込み:
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
  - 強力な .env パーサ実装:
    - export 形式対応、クォートとエスケープ、インラインコメントの適切な扱い、無効行スキップ。
    - override/protected オプションにより OS 環境変数を保護して .env.local を上書き可能。
  - 必須環境変数取得時に未設定なら ValueError を投げる _require ユーティリティ。
  - 設定プロパティ群を追加（J-Quants、kabu API、Slack、DB パス、監視閾値、環境種別・ログレベル判定など）。

- AI（自然言語処理）:
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp.score_news）を追加:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づき raw_news / news_symbols から記事を集約。
    - 銘柄ごとに記事を結合して OpenAI（gpt-4o-mini、JSON mode）へバッチ送信（最大 20 銘柄/チャンク）。
    - レスポンス検証・数値正規化・±1.0 クリップを実施し、ai_scores テーブルへ冪等更新（DELETE → INSERT）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ・リトライ、失敗はスキップして継続（フェイルセーフ）。
    - テスト時に _call_openai_api をパッチ可能な設計。
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）を追加:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して 'bull' / 'neutral' / 'bear' を日次判定。
    - マクロセンチメント取得のため raw_news からマクロキーワードで記事を抽出し、OpenAI へ投げて JSON レスポンスを解析。
    - API 失敗時は macro_sentiment=0.0 として継続、DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しに対する再試行ロジックと 5xx 判定の考慮を実装。

- データプラットフォーム（Data）:
  - マーケットカレンダー管理モジュール（kabusys.data.calendar_management）を追加:
    - market_calendar テーブルを使った営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - J-Quants から差分取得して market_calendar を更新する calendar_update_job（バックフィル・健全性チェックあり）。
    - DB が未取得時には曜日ベースのフォールバック（土日を非営業日扱い）。
  - ETL パイプライン（kabusys.data.pipeline）を追加:
    - 差分更新ロジック、J-Quants クライアント呼び出し、品質チェック呼び出し（quality モジュール）を想定。
    - ETLResult dataclass（結果集約・品質問題およびエラー情報を含む）を実装し、kabusys.data.etl で再エクスポート。
    - テーブル存在チェックや最大日付取得等のユーティリティを実装（DuckDB 前提）。
  - jquants_client を想定した fetch/save 操作との連携設計（calendar_update_job などで利用）。

- リサーチ（研究）モジュール:
  - ファクター計算（kabusys.research.factor_research）を追加:
    - Momentum ファクター: 1M/3M/6M リターン、200 日 MA 乖離を計算する calc_momentum。
    - Volatility / Liquidity 指標: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算する calc_volatility。
    - Value 指標: PER、ROE を計算する calc_value（raw_financials の最新レコードを利用）。
    - DuckDB のウィンドウ関数と SQL を活用して効率的に計算。
  - 特徴量探索（kabusys.research.feature_exploration）を追加:
    - 将来リターン算出 calc_forward_returns（任意の営業日ホライズンで LEAD を用いる）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランクベースで算出）。
    - ランク付けユーティリティ rank（同順位は平均ランク処理）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）の算出。
  - research パッケージで主要関数を __all__ にて公開。

### 変更 (Changed)
- OpenAI API 呼び出し周りの堅牢性設計を整備:
  - JSON モードでの応答に対し、前後に混入した余計なテキストから最外の {} を抽出して復元する耐性を実装。
  - APIError の status_code の有無に対応する保護ロジックを実装（未来の SDK 変更に耐える）。
- DuckDB への書き込みは冪等性を重視（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK の使用）。部分失敗時に既存データを保護するために対象コードを限定して DELETE を実行する設計。

### 修正 (Fixed)
- ETL / データ更新系で DuckDB executemany に空リストを渡すと失敗する問題に対処する為、空チェックを追加（DuckDB 0.10 対応）。
- market_calendar の NULL 値が存在する場合に警告を出し、曜日ベースフォールバックに戻るように安全にハンドル。

### セキュリティ (Security)
- 必須の機密情報（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）は settings にて必須チェックを実施。未設定時は ValueError を送出して安全性を確保。

### テスト性 (Testing)
- AI 呼び出し部分（kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api）は unittest.mock.patch により差し替え可能とし、外部 API に依存しないテストが可能。

### 既知の制限・設計上の注記
- 現時点では PBR や配当利回り等のバリュー指標は未実装（calc_value に注記あり）。
- ETL の具体的な jquants_client 実装や quality モジュールの詳細はこのコード断片からは含まれていないため、外部実装に依存。
- News/Regime AI 処理は OpenAI（gpt-4o-mini）の JSON mode に依存しており、レスポンス仕様の変更があった場合はパーサの改修が必要。

---

（注）本 CHANGELOG は提供されたコード断片の内容を基に推測して作成した初回リリース向けの記述です。実際の変更履歴やリリース日、細かい API 仕様はリポジトリの履歴・チケットに基づいて調整してください。
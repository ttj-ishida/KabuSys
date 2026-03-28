# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初期リリースを記録しています。

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース。日本株自動売買システムの基盤を提供する以下の主要モジュールを追加。
  - kabusys.config
    - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの検出は __file__ から親ディレクトリを探索し `.git` または `pyproject.toml` を基準とするため、CWDに依存しない実装。
    - 読み込み優先順位: OS 環境 > .env.local > .env。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを抑止可能。
    - .env のパースは `export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
    - 必須設定の取得ヘルパー `_require` と、環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）の追加。
    - 設定プロパティ（J-Quants、kabuステーション、Slack、DBパスなど）の公開（`settings`）。
  - kabusys.ai.news_nlp
    - raw_news テーブルのニュースを OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄ごとのスコアを ai_scores テーブルへ書き込む `score_news` を実装。
    - スコアリングのタイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ `calc_news_window` を追加。
    - バッチング（最大20銘柄/呼び出し）、1銘柄あたりの記事上限（件数・文字数）によるトリム、リートライ（429/ネットワーク/タイムアウト/5xx）ロジック、レスポンスの厳格なバリデーションを実装。
    - DuckDB 互換性（executemany の空リスト回避）やフェイルセーフ（API失敗時はスキップし処理続行）を組み込み。
  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュース由来の LLM センチメント（重み30%）を合成し、日次の市場レジーム（`bull` / `neutral` / `bear`）を判定する `score_regime` を実装。
    - マクロニュース抽出・LLM 呼び出し（gpt-4o-mini）・リトライ・フェイルセーフ（API失敗時は macro_sentiment=0.0）を含む堅牢な処理フローを提供。
    - DB へは冪等性を保ったトランザクション（BEGIN / DELETE / INSERT / COMMIT）で書き込み、失敗時は ROLLBACK を行う。
  - kabusys.research
    - ファクター計算モジュール `factor_research`：モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日ATR）、バリュー（PER/ROE）などを DuckDB 上の prices_daily / raw_financials から算出する関数を追加（`calc_momentum`, `calc_volatility`, `calc_value`）。
    - 特徴量探索モジュール `feature_exploration`：将来リターン算出（`calc_forward_returns`）、IC（スピアマン順位相関）計算（`calc_ic`）、ランク変換（`rank`）、統計サマリー（`factor_summary`）を追加。外部ライブラリに依存せず標準ライブラリのみで実装。
    - 研究用ユーティリティとして `zscore_normalize` を `kabusys.data.stats` から再エクスポート。
  - kabusys.data
    - カレンダー管理（`calendar_management`）
      - JPX 市場カレンダーの夜間バッチ更新ジョブ `calendar_update_job`（J-Quants API 経由で差分取得して `market_calendar` を冪等保存）を追加。
      - 営業日判定ヘルパー群（`is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`）を提供。market_calendar が未取得の際は曜日ベースでフォールバック。
      - バックフィル、ルックアヘッド、健全性チェックの実装により安全な更新を担保。
    - ETL パイプライン（`pipeline`）
      - 差分取得・保存・品質チェックフローを想定した ETLResult データクラスを追加（取得/保存件数、品質問題リスト、エラーリスト等を保持）。
      - DuckDB 上での最大日付取得等のユーティリティを実装。
    - `etl` モジュールから ETLResult を再エクスポート。
  - パッケージ公開インターフェース調整
    - kabusys.__init__ でバージョン（0.1.0）と公開パッケージ（data, strategy, execution, monitoring）の __all__ を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは関数引数経由または環境変数 OPENAI_API_KEY を参照する設計。APIキー未設定時は ValueError を発生させ明示的に要求。

### Notes / 実装上の留意点
- 全体設計の共通方針
  - ルックアヘッドバイアス防止のため、各モジュールは datetime.today() / date.today() を直接参照せず、呼び出し側から `target_date` を受け取る設計。
  - 外部 API 呼び出し（OpenAI / J-Quants 等）はリトライとフェイルセーフを組み込み、部分的な API 失敗がシステム全体を停止させないようにしている。
  - DuckDB のバージョン互換性を考慮した実装（executemany の空リスト回避など）。
  - データベース書き込みは可能な限り冪等性を保つ（DELETE→INSERT、ON CONFLICT 想定）実装。
- .env 取り扱い
  - .env の複雑なケース（クォート内のエスケープ、コメント、export プレフィックス）に対応しているため、既存の .env を移行する際の互換性が高い。
  - ただし OS 環境変数はデフォルトで保護され、`.env.local` による上書きが可能。

---

今後のリリースでは、ユニットテスト例、Strategy / Execution / Monitoring の具象実装、より詳細な品質チェックとモニタリングアラート機能などを追加予定です。
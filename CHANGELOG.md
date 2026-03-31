# Changelog

すべての注目すべき変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

なお、本ファイルはコードベース（src/kabusys 以下）から実装状況を推測して作成しています。実際の変更履歴ファイルが存在する場合はそちらを優先してください。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回公開リリース（推定）。以下の主要機能を含みます。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を想定（__all__）。

- 設定管理
  - kabusys.config:
    - .env ファイルおよび環境変数の読み込み機構を実装。プロジェクトルート検出は .git または pyproject.toml を基準に行うため、CWD に依存しない自動ロードを提供。
    - .env のパースは export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントなど多くの形式に対応。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - OS 環境変数を protected として .env.local による上書きから保護する挙動を実装（.env.local は OS 環境変数を除き上書き）。
    - 必須環境変数を取得する _require() と Settings クラスを提供。J-Quants / kabuステーション / Slack / DB / 監視 / システム設定（KABUSYS_ENV, LOG_LEVEL）用のプロパティを備える。env 値・log_level は検証済み。

- AI（自然言語処理）機能
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON モードを用いて銘柄ごとのニュースセンチメント（ai_score）を算出し ai_scores テーブルへ書き込む。
    - バッチ処理（1コールあたり最大 20 銘柄）、1 銘柄あたりの記事数上限・文字数トリム、レスポンス検証、スコアの ±1.0 切り捨て、リトライ（指数バックオフ）などの堅牢化を実装。
    - calc_news_window() により JST ベースのニュース取得ウィンドウ（前日15:00〜当日08:30）を正確に扱う。
    - API キー注入（引数 or 環境変数 OPENAI_API_KEY）をサポート。API 呼び出し箇所はテストで差し替え可能に設計。

  - kabusys.ai.regime_detector:
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする score_regime を実装。
    - マクロニュースの抽出（マクロキーワードによるフィルタ）、OpenAI 呼び出し（gpt-4o-mini + JSON mode）、API 失敗時のフェイルセーフ（macro_sentiment=0.0）、リトライ/バックオフ処理を実装。
    - ルックアヘッドバイアス回避の設計（target_date 未満のデータのみ使用、datetime.today() 不使用）。

- リサーチ / ファクター
  - kabusys.research.factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）および流動性指標の計算関数（calc_momentum, calc_volatility, calc_value）を実装。DuckDB を用いた SQL ベースの計算を行う。
    - データ不足時の None 返却、計算日を基準にした正確なウィンドウ処理、ログ出力を備える。

  - kabusys.research.feature_exploration:
    - 将来リターン計算 calc_forward_returns（デフォルト horizons=[1,5,21]）、IC（Information Coefficient）計算 calc_ic（スピアマン ρ ランク相関）、値のランク化ユーティリティ rank、ファクター統計量 summary を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで処理を実装。

- データプラットフォーム
  - kabusys.data.calendar_management:
    - market_calendar テーブルを用いた営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を実装。DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫したロジックを採用。
    - calendar_update_job により J-Quants からの差分取得・バックフィル・健全性チェック（将来日付の異常検出）を行い、冪等に保存するジョブを実装。

  - kabusys.data.pipeline / etl:
    - ETLResult データクラスを公開し、ETL パイプラインの基本設計（差分更新、backfill、品質チェック保護、id_token 注入）を反映。
    - _table_exists / _get_max_date（※未完の可能性あり）等のユーティリティ関数を追加。
    - kabusys.data.etl モジュールで ETLResult を再エクスポート。

### 変更 (Changed)
- 設計上の方針や注意点をコード内ドキュメンテーションに多数追加（ルックアヘッドバイアス防止、DuckDB 互換性、部分失敗時のデータ保護など）。

### 修正 (Fixed)
- （初回リリースのため特別なバグ修正履歴は無し。ただし以下「既知の問題」を参照。）

### 既知の問題 (Known issues)
- ETL パイプライン実装の一部:
  - src/kabusys/data/pipeline.py 内の _get_max_date 関数付近でコードが途中（"return date.fro" のような断片）で切れている箇所が見られ、関数実装が未完である可能性があります。これに伴い一部 ETL ユーティリティが正しく動作しない可能性があります（要修正）。
- パッケージ公開インターフェース:
  - kabusys.__init__ では "strategy", "execution", "monitoring" を __all__ に含めているが、今回のスナップショットではそれらのモジュール/パッケージの実装が提示されていないため、実際の公開 API としては未完成または別ソースで提供される想定です。
- OpenAI 統合:
  - gpt-4o-mini を利用する実装で、JSON mode を期待するレスポンスパースを行う設計。LLM の挙動や API のバージョン差分に依存するため、実運用時は応答フォーマットの変化に対する監視・テストが必要です。
- DuckDB バインド互換性:
  - executemany に空リストを渡すとエラーになる DuckDB のバージョン依存対応が入っているものの、実環境の DuckDB バージョン差分で追加の調整が必要になる可能性があります。

### セキュリティ (Security)
- 現状、機密情報（OpenAI API キー等）は環境変数で扱う設計。自動 .env ロード機構には protected な OS 環境変数セットを考慮しており、.env.local による上書き挙動も制御されています。運用時は .env の取り扱いに十分注意してください。

---

次バージョンでは上記の既知の問題修正（pipeline._get_max_date 完成、strategy/execution/monitoring の実装整備）、およびテストケース・CI での OpenAI/DB 依存部分のモック化を推奨します。
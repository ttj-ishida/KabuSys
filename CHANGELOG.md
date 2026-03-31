# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-31
初回リリース。パッケージのコア機能を実装しました（データETL・マーケットカレンダー・ファクター計算・ニュースNLP・市場レジーム判定・設定管理など）。

### 追加
- パッケージエントリポイント
  - src/kabusys/__init__.py によりパッケージを公開。バージョンは 0.1.0。公開モジュール: data, strategy, execution, monitoring（strategy/execution/monitoring は公開名として含まれるが、このリリースに含まれる具体実装は一部モジュールで不明）。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env / .env.local ファイルの自動読み込み機能（プロジェクトルート判定は .git または pyproject.toml を使用）。
    - export KEY=val 形式や引用符付き値、インラインコメントの扱いを考慮した堅牢な .env パーサーを実装。
    - OS 環境変数の保護（既存の環境変数はデフォルトで上書きしない）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - Settings クラスを提供し、主要な設定（J-Quants / kabuAPI / Slack / DB パス / 監視閾値 / 環境・ログレベル判定）をプロパティとして取得。値の検証（KABUSYS_ENV, LOG_LEVEL）を実装。

- AI（ニュースNLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を使い銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini） を用いたバッチセンチメント解析を実装。
    - API バッチサイズ、文字数・記事数トリム、エクスポネンシャルバックオフ、結果バリデーション、スコアの ±1.0 クリップ、DuckDB への冪等的書き込み（DELETE → INSERT）を実装。
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を直接参照せず、target_date ベースで計算。

  - src/kabusys/ai/regime_detector.py
    - ETF（1321、日経225連動）200日移動平均乖離（重み 70%）とニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出・保存する機能を実装。
    - OpenAI 呼び出しのリトライ・フォールバック（失敗時 macro_sentiment=0.0）・レスポンスパースの堅牢化・スコアクリップを実装。
    - DuckDB を用いた冪等的な market_regime テーブルへの書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時はROLLBACK）。

- データプラットフォーム
  - src/kabusys/data/etl.py
    - ETLResult を公開インターフェースとして再エクスポート。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインの骨組みと ETLResult dataclass を実装。差分取得・保存・品質チェック（quality モジュール）を想定した設計。
    - ETL 実行結果のシリアライズメソッド（to_dict）により品質問題を分かりやすく出力可能。

  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）の参照・更新ロジックを実装。
    - 営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が不足する場合は曜日ベース（平日＝営業日）でのフォールバックを行うことで堅牢性を確保。
    - calendar_update_job により J-Quants クライアント（jquants_client.fetch_market_calendar / save_market_calendar）を用いた夜間差分更新とバックフィル、健全性チェックを実装。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M リターン、200日移動平均乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）などのファクター計算を実装。DuckDB SQL を主体にしており、結果は (date, code) をキーとする dict のリストで返却。
    - 欠損データやデータ不足時の None ハンドリングを実装。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず、標準ライブラリと DuckDB のみで実装。

### 変更（設計上の重要点）
- AI モジュール全般においてルックアヘッドバイアス回避の方針を採用（target_date ベースのウィンドウ計算、date.today() を直接使用しない）。
- OpenAI 呼び出しは JSON mode を想定した厳格なパース/バリデーションを行い、異常応答時は安全にフォールバックする設計。
- DuckDB に対する更新処理は明示的トランザクション（BEGIN / COMMIT / ROLLBACK）を使用して冪等性および部分失敗時の保護を実装。
- .env パーサーの挙動（クォート、エスケープ、コメント、export プレフィックス対応）を細かく制御し、実運用での柔軟性を確保。

### 修正（エラー処理 / フォールバック）
- OpenAI API 呼び出しに対して:
  - RateLimitError/接続エラー/タイムアウト/5xx をリトライ対象とし、指数バックオフで再試行。
  - 永続的失敗時はログ出力し、処理を継続（該当結果は 0.0 またはスキップにフォールバック）。
- JSON レスポンスのパース失敗・フォーマット不正時は警告ログを出力し、そのチャンクをスキップ（例外を上位に伝播させない方針）。
- DuckDB executemany への空リストバインドに関する回避（空時は実行をスキップ）を実装。

### 未実装 / 注意点
- パッケージ公開名として strategy, execution, monitoring が __all__ に含まれていますが、今回提示されたコードスニペット内にこれらの完全な実装が含まれていないため、実装状況に注意してください（将来的に追加・拡張を想定）。
- J-Quants や kabu API クライアント（jquants_client など）は参照されるが、実装は別モジュールに存在する想定。外部 API 依存部分はテスト時にモックすることが推奨されます。

---

今後のリリースでは、strategy/ execution/monitoring の具体的実装、テストカバレッジの追加、運用上の設定例（.env.example）やマイグレーションスクリプトの追加を予定しています。必要があれば CHANGELOG をより細かく分割して作成します。
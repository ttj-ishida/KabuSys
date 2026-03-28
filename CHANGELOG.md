# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

版管理:
- 現在のパッケージバージョン: 0.1.0 (src/kabusys/__init__.py)

[Unreleased]
- （今後の変更を記載してください）

[0.1.0] - 2026-03-28
Added
- パッケージ初版を追加。
  - パッケージメタ情報: kabusys/__init__.py にて __version__ = "0.1.0" を設定。
- 環境設定/自動 .env ロード機能を追加（kabusys.config）。
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - export KEY=val 形式、クォート・エスケープ、インラインコメントの取り扱いをサポートする .env パーサ実装。
  - protected（OS 環境変数の保護）や override オプションにより上書き挙動を制御。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / 環境種別 / ログレベル等のプロパティを環境変数から取得・検証。
  - 必須パラメータ未設定時は明示的なエラー（ValueError）を発生させる。

- AI（OpenAI）を用いたニュース系機能を追加（kabusys.ai）。
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini、JSON Mode）へ送信しセンチメント（ai_score）を算出して ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄/コール）、記事数・文字数のトリム、レスポンス検証、スコアの ±1.0 クリップを実装。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を実装。
    - レスポンスの JSON パース耐性（前後余計テキストからの {} 抽出）やレスポンス検証ロジックを実装。
    - テスト用に API 呼び出し部分を差し替え可能（_call_openai_api のパッチを想定）。
    - ルックアヘッドバイアス対策として datetime.today() を参照しない設計。
  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードフィルタ、OpenAI 呼び出し、複数回リトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - ma200_ratio の計算、レジームスコア合成、冪等的に market_regime テーブルへ書込（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - news_nlp とは API 呼び出し実装を分離しモジュール結合を抑制。

- Data / ETL / カレンダー周りの実装を追加（kabusys.data）。
  - calendar_management モジュール
    - market_calendar テーブルを利用した営業日判定関数群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベースのフォールバック（週末非営業）を採用。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する calendar_update_job を実装（バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数制限と date 型のみを扱う設計で安全性を確保。
  - pipeline / etl モジュール
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl から再エクスポート）。
    - 差分取得、保存（jquants_client の idempotent save_* を期待）、品質チェック統合のためのユーティリティ基盤を実装。
    - _get_max_date 等の DB ヘルパー、バックフィル挙動、品質問題の収集（致命的エラーはフラグとして保持）を実装。

- Research（ファクター計算・特徴量解析）モジュールを追加（kabusys.research）。
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、
      バリュー（PER, ROE）、流動性指標の計算関数（calc_momentum, calc_volatility, calc_value）を追加。
    - DuckDB 上の prices_daily / raw_financials テーブルのみ参照し、データ不足時の None ハンドリングを実装。
    - 実装は SQL ウィンドウ関数を多用して効率化。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、
      ランク変換（rank）、ファクター統計サマリ（factor_summary）を追加。
    - Spearman（ランク）相関の実装や ties の平均ランク処理、外部ライブラリ非依存の純 Python 実装。

Changed
- （初版のため特になし）

Fixed
- （初版のため特になし）

Deprecated
- （初版のため特になし）

Security
- OpenAI API キー未設定時に明示的に ValueError を発生させることで誤動作を防止（news_nlp / regime_detector）。

Notes / 設計上の留意点
- ルックアヘッドバイアス防止: 各 AI / 研究 / ETL モジュールは datetime.today() / date.today() を内部参照せず、呼び出し元から target_date を与える設計。
- フェイルセーフ: 外部 API 失敗時は例外を無闇に投げず、ゼロスコアやスキップで継続する箇所がある（運用の頑健性重視）。
- DuckDB を前提とした SQL / executemany の互換性考慮（空リストの executemany を避ける実装など）。
- テスト容易性: OpenAI 呼び出し箇所をパッチ差し替え可能にしてユニットテストを容易にする設計。

今後の改善候補（参考）
- news_nlp / regime_detector の OpenAI クライアント周りに共通実装を導入して重複削減。
- カレンダー更新のジョブに対するより詳細な監査ログやメトリクス収集。
- ETL の並列化、API コールのレート制御ポリシー明確化。
- ai スコアの検証・モニタリングダッシュボード連携（Slack 通知等）。

---
（この CHANGELOG は、提供されたコードベースから推測して作成しています。実際のコミット履歴・リリースメモがある場合はそちらを優先してください。）
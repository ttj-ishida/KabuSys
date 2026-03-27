Changelog
=========
すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

[0.1.0] - 2026-03-27
-------------------

Added
- 初回リリース: kabusys パッケージを追加。目的は日本株のデータパイプライン、リサーチ、AI支援によるニュース/レジーム判定、及び自動売買支援の基盤機能提供。
  - パッケージ公開点:
    - src/kabusys/__init__.py: バージョン管理と公開モジュール定義（data, strategy, execution, monitoring）。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサー（export 対応、クォート・エスケープ、インラインコメントの扱い等）。
  - OS 環境変数を保護する protected 上書き制御。
  - Settings クラスを公開（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル等のプロパティとバリデーション）。
- AI モジュール（src/kabusys/ai/*）
  - ニュースNLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込み。
    - チャンク処理（デフォルト 20 銘柄/チャンク）、1 銘柄あたりの記事数上限・文字数トリム、レスポンスバリデーション、スコアの ±1.0 クリップ。
    - リトライ（429, ネットワーク断, タイムアウト, 5xx）に対する指数バックオフ。
    - テスト性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch）。
    - calc_news_window（タイムウィンドウ計算）を実装（JST 基準の前日 15:00 ～ 当日 08:30 に対応）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等保存。
    - マクロニュース抽出用キーワード群、OpenAI（gpt-4o-mini）呼び出し、リトライ・フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - _calc_ma200_ratio ではルックアヘッド防止のため target_date 未満のデータのみ使用、データ不足時は中立（1.0）にフォールバック。
- Research モジュール（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と価格結合による PER / ROE 計算（EPS が 0/欠損時は None）。
    - DuckDB ベースの実装（prices_daily / raw_financials のみ参照）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン先の将来リターン（LEAD を利用）。
    - calc_ic: スピアマン（ランク）による Information Coefficient 計算（rank ユーティリティを含む）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
  - re-export：zscore_normalize（kabusys.data.stats）を research パッケージの一部として公開。
- Data モジュール（src/kabusys/data/*）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の提供。
    - DB データ優先・未登録日は曜日ベース（週末非営業）でフォールバックする設計。
    - calendar_update_job: J-Quants API から差分取得して冪等保存（バックフィル・健全性チェックあり）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを定義して ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約して返却。
    - 差分取得・backfill・品質チェック（quality モジュール利用）を想定した設計（詳細は pipeline モジュールに実装予定/拡張）。
    - etl.py は ETLResult を再エクスポート。
  - DuckDB を主要ストレージとして利用する設計（複数モジュールで DuckDB 接続を引数に受ける）。
- テスト設計の配慮
  - 主要な外部 API 呼び出し（OpenAI クライアント呼び出し）は関数化して patch/差し替えしやすくしている（ユニットテストでモック可能）。
  - DuckDB executemany に対する互換性考慮（空リスト送信回避）。
- ロギング / フェイルセーフ
  - API 失敗やデータ不足時のフォールバック値（例: macro_sentiment=0.0、ma200_ratio=1.0、スコア未取得時はスキップ）を明示的に実装。
  - トランザクションは BEGIN / DELETE / INSERT / COMMIT を用い、例外時は ROLLBACK を実施（ROLLBACK 失敗時の警告ログあり）。

Notes / 要件
- 必須環境変数:
  - OPENAI_API_KEY（AI 関連関数の呼び出しに必須）
  - JQUANTS_REFRESH_TOKEN（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD（Settings.kabu_api_password）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 関連）
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb（Settings.duckdb_path）
  - SQLite (monitoring): data/monitoring.db（Settings.sqlite_path）
- 日付・時間設計:
  - 主要関数は内部で datetime.today()/date.today() を参照しない（target_date を引数に取り、ルックアヘッドバイアスを防止）。
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON Mode（response_format={"type":"json_object"}）で行う。API レスポンスのフォーマットに厳密に依存するため、運用時はモデル・フォーマットの互換性に注意。

Breaking Changes
- なし（初回リリース）。

Security
- 特記なし。

今後の予定（短期的な Roadmap）
- pipeline の ETL 実装を完成させ、jquants_client 連携を公的な API 経路で統合。
- strategy / execution / monitoring モジュールの実装・公開（パッケージ __all__ にあるが未実装分の充足）。
- 単体テスト・CI の整備、運用監視（Slack 通知等）の追加。
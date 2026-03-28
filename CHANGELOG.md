Changelog
=========

すべての重要な変更点はこのファイルに記録します。本ファイルは Keep a Changelog の形式に従います。
リリース日付はコードベースから推測して記載しています。

フォーマット: [バージョン] - YYYY-MM-DD

[0.1.0] - 2026-03-28
--------------------

Added
- 初回公開: kabusys パッケージ（日本株自動売買システムの基礎機能群）。
  - パッケージ公開情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env / .env.local からの自動読み込みを実装。プロジェクトルートは .git または pyproject.toml を基準に探索して決定。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードの無効化が可能。
  - export 形式やクォート・コメントを考慮した .env 行パーサを実装。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティとバリデーションを公開。
- AI 関連（src/kabusys/ai/）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_score）を算出、ai_scores テーブルへ冪等的に書き込み。
    - バッチサイズ制御、1銘柄あたりの最大記事数・文字数トリム、JSON Mode での応答パース、レスポンス整合性検証を実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ（最大回数制御）。
    - API 呼び出し部分はテスト容易性のため差し替え可能（_call_openai_api を patch 可能）。
    - calc_news_window ユーティリティを実装（JST基準のニュースウィンドウ計算）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と LLM によるマクロセンチメント（重み30%）を合成して market_regime テーブルに判定結果を書き込む score_regime を実装。
    - LLM 呼び出しは独立実装でモジュール結合を避け、API障害時には macro_sentiment=0.0 として継続するフォールバックを採用。
    - DuckDB クエリでのルックアヘッドバイアス対策（target_date 未満データのみ使用）を採用。
- データ基盤（src/kabusys/data/）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを基に営業日判定ロジック（is_trading_day/is_sq_day/next_trading_day/prev_trading_day/get_trading_days）を提供。
    - DB データがない場合は曜日ベース（土日非営業）でフォールバック。
    - calendar_update_job により J-Quants API から差分取得し冪等保存（バックフィル・健全性チェック含む）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを導入して ETL 実行結果（取得・保存件数、品質問題、エラー）を表現。
    - 差分取得・バックフィル・品質チェックの設計方針を実装（DB 最大日付取得ユーティリティ等）。
    - data.etl モジュールで ETLResult を再エクスポート。
  - DuckDB 互換性対応や日付変換ユーティリティ等を提供。
- リサーチ（src/kabusys/research/）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）を計算する関数を実装。
    - DuckDB SQL / ウィンドウ関数を利用した効率的な実装。データ不足時は None を返す設計。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas など外部依存無しで実装し、研究用途での解析を想定。
  - research パッケージ __all__ に主要関数を公開。

Changed / Improved
- OpenAI API 呼び出しの堅牢化
  - JSON レスポンスのパース失敗時に前後余計なテキストが混ざるケースから {} を抽出して復元する処理を追加（news_nlp）。
  - APIError の status_code を安全に取得して 5xx の場合はリトライ、非5xx は即スキップするロジックを実装（regime_detector/news_nlp）。
  - リトライ時に指数バックオフを適用し、リトライ回数超過時は警告ログを出してフォールバックする設計。
- データベース操作の互換性と安全性向上
  - DuckDB の executemany に対する注意（空リスト不可）を考慮し、空チェックを行った上で DELETE/INSERT を実行。
  - market_calendar やその他存在チェック用ユーティリティを導入してテーブルがない場合の安全なフォールバックを提供。
  - 日付値の変換ユーティリティ（_to_date）を追加して DuckDB 返却値を安全に date に変換。
- テスト容易性
  - OpenAI 呼び出しをモジュール内のプライベート関数として分離し、unittest.mock.patch による差し替えを想定した設計（テスト時に外部 API をモック可能）。
- バイアス回避設計
  - score_news / score_regime 等の関数は内部で datetime.today() / date.today() を参照せず、引数で target_date を受け取る仕様によりルックアヘッドバイアスを防止。

Fixed
- レスポンス処理の堅牢性向上により、LLM からの不整合な応答や部分的な失敗が発生しても他の銘柄やデータ処理への影響を最小化する挙動に修正（部分失敗時に既存スコアを消さないためのコード絞り込み等）。

Notes / その他
- 設計文書への準拠: 各モジュールの docstring において DataPlatform.md / StrategyModel.md 等の設計方針に従った実装である旨を明記。
- 外部依存: OpenAI SDK・duckdb を利用。実行には適切な環境変数（OPENAI_API_KEY 等）や .env の設定が必要。
- セキュリティ: 環境変数の自動上書きを防止する protected 機能を実装（OS 環境変数保護）。

未リリース / 将来検討
- PBR・配当利回り等、バリューファクターの拡張（現バージョンでは未実装）。
- ai モジュールにおけるモデルやプロンプト改善、より細かなエラーメトリクスの導入。
- calendar_update_job のより詳細な監視・メトリクス出力。

---
Keep a Changelog に準拠した CHANGELOG.md（日本語）

すべての注目すべき変更をこのファイルに記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
- （なし）

[0.1.0] - 2026-04-03
Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開情報
    - src/kabusys/__init__.py によりバージョンと公開モジュール一覧を宣言（data, strategy, execution, monitoring）。
- 環境設定・ロード機能（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能をプロジェクトルート（.git または pyproject.toml を探索）に基づいて実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
  - OS 環境変数を保護する protected 上書きロジック、override フラグをサポート。
  - Settings クラスでアプリケーション設定をプロパティとして公開（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境判定 / ログレベル 等）。
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）、必須環境変数未設定時は明示的なエラーを送出。
- ニュースNLP（AI）パイプライン（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を集約して銘柄ごとにテキストをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄単位のセンチメント（ai_score）を算出。
  - タイムウィンドウ計算（JST基準で前日15:00〜当日08:30に相当する UTC 範囲）を提供する calc_news_window。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、1銘柄あたりの最大記事数・文字数トリムによるトークン肥大化対策。
  - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ（リトライ上限、ログ出力）。
  - API レスポンスの堅牢なバリデーション実装（JSON 抽出、results 構造、コード整合性、数値検査、スコア ±1.0 クリップ）。
  - 書込みは冪等（DELETE → INSERT）で実施し、部分失敗時に既存スコアを保護（DuckDB の executemany の扱いに配慮）。
  - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
- 市場レジーム判定（AI + 指標合成）（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - prices_daily からのデータ取得はルックアヘッドを防ぐため target_date 未満のみを参照する実装。
  - マクロニュース抽出（タイトルベースでキーワードフィルタ、最大記事数制限） → OpenAI によるセンチメント評価 → フォールバック macro_sentiment=0.0（API失敗時）。
  - OpenAI 呼び出しに対するリトライ・5xx 判定・タイムアウト処理、レスポンス JSON パース失敗時のフォールバック。
  - market_regime テーブルへの冪等なトランザクション書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
  - テスト用に _call_openai_api と分離した設計。
- データプラットフォーム（DuckDB ベース）ユーティリティ（src/kabusys/data/）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理関数群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar がない/未登録日の場合は曜日（平日）ベースのフォールバック。
    - 最大探索日数による無限ループ防止、DB優先の一貫した判定ロジック。
    - calendar_update_job により J-Quants からの差分取得 → 保存（バックフィル/健全性チェックを含む）を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass による ETL 実行結果の集約（取得数・保存数・品質問題・エラー一覧・便利メソッド）。
    - 差分更新・バックフィル・品質チェックの設計方針に基づく実装基盤（jquants_client と quality モジュール連携を想定）。
    - DuckDB テーブル存在チェック、最大日付取得等のユーティリティを実装。
  - jquants_client との連携を前提とした idempotent 保存・差分取得設計（実装ファイルは jquants_client を参照）。
- 研究用分析モジュール（src/kabusys/research/）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: mom_1m/mom_3m/mom_6m と ma200_dev（200日 MA 乖離）計算（データ不足時は None）。
    - ボラティリティ/流動性: atr_20, atr_pct, avg_turnover, volume_ratio を計算。
    - バリュー: EPS と株価から PER を算出、ROE を raw_financials から取得（最新レポートを銘柄毎に選択）。
    - DuckDB のウィンドウ関数と SQL を活用した効率的な集計実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（複数ホライズンに対応、入力検証、効率を考慮した期間スキャン）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンランク相関、欠損/定数分離の扱い）。
    - ランク関数 rank（同順位は平均ランク、浮動小数対策に round）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median を算出、None を除外）。
  - 研究 API の公開 (research.__init__.py) により主要関数を再エクスポート。
- 共通設計方針・品質ポイント
  - ルックアヘッドバイアス防止のため、すべての「日次判定/スコア作成」処理は内部で datetime.today()/date.today() を直接参照しない（target_date パラメータを必須使用）。
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢なパースとバリデーションを実装。
  - API 通信には堅牢なリトライ（指数バックオフ）を実装し、致命的失敗を避けるためフェイルセーフのデフォルト値（例: macro_sentiment=0.0）を用意。
  - DuckDB をストレージとして利用し、トランザクション（BEGIN/COMMIT/ROLLBACK）での安全な書き込みを行う。
  - テスト容易性: API 呼び出しの差し替えポイント（_call_openai_api）や、api_key を引数注入可能にするなどの配慮。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Removed
- （初回リリースのためなし）

Security
- 環境変数の自動ロードは既存の OS 環境変数を上書きしない既定動作とし、重要な OS 環境を protected として保持。
- OpenAI API キーは明示的に環境変数（OPENAI_API_KEY）または関数引数で渡す仕様。未設定時は ValueError を送出して誤動作を防止。

Notes / Usage
- 依存: duckdb, openai（OpenAI SDK）などが必要。実行前に必要環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を .env に設定するか環境変数で渡してください。
- 自動 .env ロードの動作はプロジェクトルート検出に依存します。パッケージ配布やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能です。
- AI 系処理（score_news, score_regime）は API 呼び出し回数とコストが発生するため、実行頻度に注意してください。

今後の予定（参考）
- strategy / execution / monitoring モジュールの実装完成・ドキュメント整備。
- テストカバレッジ増強（ユニットテスト／統合テスト）。
- CLI / バッチスケジューラ統合、運用監視用のエクスポート強化。

---  
貢献・バグ報告は Issue/PR を通してお願いします。
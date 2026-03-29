CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠し、
セマンティックバージョニングを使用します。

未リリース
--------

- なし

[0.1.0] - 2026-03-29
--------------------

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。
主にデータ取得/管理、研究用ファクター計算、ニュースNLP・市場レジーム判定のAI連携、
および環境設定ユーティリティを含みます。

Added
- パッケージ初期化
  - src/kabusys/__init__.py にて初期バージョン 0.1.0 を定義。公開サブパッケージ: data, research, ai, monitoring, strategy, execution。

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数保護（protected set）をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト用）。
    - .env パーサの実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープに対応）。
    - Settings クラスを提供し、アプリ全体で環境設定を取得可能に（必須チェック、値検証、便利プロパティ）。
    - 期待される主な環境変数:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development/paper_trading/live）, LOG_LEVEL

- ニュースNLP（AI）モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ保存する処理を実装。
    - バッチ送信（最大 20 銘柄/チャンク）、1 銘柄あたり記事数上限と文字数トリムを実装（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - 再試行（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで実施。失敗時は当該チャンクをスキップして継続（フェイルセーフ）。
    - レスポンス検証ロジックを実装（JSON 復元、results の存在チェック、code 照合、数値変換、値のクリップ）。
    - calc_news_window(target_date) により JST ベースのニュース収集ウィンドウを厳密に計算（ルックアヘッド回避）。
    - API キー注入可能（引数または OPENAI_API_KEY 環境変数）。

  - テスト容易性: OpenAI 呼び出しを差し替え可能な内部ラッパー（_call_openai_api）を用意。

- 市場レジーム判定モジュール
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の算出（target_date 未満のデータのみ使用。データ不足時は中立 1.0 を返す）と、マクロニュース抽出（キーワードフィルタ）を実装。
    - OpenAI（gpt-4o-mini）呼び出しで JSON を期待、API エラー時はマクロセンチメントを 0.0 にフォールバック。
    - レジーム合成ルール・閾値（BULL/Bear）を定義し、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API キー注入可能（引数または OPENAI_API_KEY 環境変数）。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（duckdb SQL を活用）。
    - Volatility & Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - Value: raw_financials からの EPS/ROE を利用して PER/ROE を算出（最新財務レコードの取得ロジック含む）。
    - いずれもルックアヘッドバイアス対策やデータ不足時の None ハンドリングを実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンを一度のクエリで取得。horizons の検証あり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（同順位は平均ランク）。
    - rank と factor_summary（count/mean/std/min/max/median）のユーティリティを実装。
  - src/kabusys/research/__init__.py にて主要関数を公開。

- データ（Data）モジュール
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値を優先、未登録日は曜日ベースでフォールバック。最大探索幅制限で無限ループ回避。
    - calendar_update_job による J-Quants からの差分取得 → 保存フロー（バックフィルと健全性チェック含む）。
  - src/kabusys/data/pipeline.py
    - ETL の設計に沿ったユーティリティを実装。
    - ETLResult dataclass を定義（取得件数、保存件数、品質問題、エラー一覧を含む）。to_dict によるシリアライズ対応。
    - テーブル最終日取得や存在チェック等の内部ユーティリティを実装。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。

- その他
  - DuckDB を主なローカル分析 DB として想定。多くの処理が DuckDB 接続（DuckDBPyConnection）を受け取り SQL/Window 関数を利用して実装。
  - 設計方針として「ルックアヘッドバイアスを避ける」「API 呼び出しはフェイルセーフに（例外を全体に波及させない）」「DB 書き込みは冪等に」を徹底。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- OpenAI API キーや他の機密情報は環境変数経由で扱う想定。.env 自動読み込み機能はあるが、KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト時や安全な初期化で無効化可能。

重要な移行 / 運用ノート
- 必須データベーステーブル（少なくとも以下が存在する想定）
  - prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_regime, market_calendar
- OpenAI 連携を使用する機能（news_nlp, regime_detector）は OPENAI_API_KEY の設定が必須（または関数引数で明示的に渡す）。
- .env 処理の詳細
  - export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、インラインコメント（スペース直前の # をコメント扱い）などに対応。
  - .env.local は .env より優先して上書き（ただし OS 環境変数は保護される）。
- DuckDB の特性
  - executemany に空リストを渡せない（DuckDB 0.10 の挙動）ため、該当箇所で空チェックを入れている。
- 動作上のフェイルセーフ
  - AI 呼び出し失敗時はそのスコアを 0（中立）にフォールバックするか、該当チャンクをスキップして残り処理を継続します。これは運用での停止回避設計です。

今後の予定（参考）
- モデルやプロンプトの改善、news_nlp の並列化やコスト最適化、ETL のより詳細な品質チェックや監視・アラート統合などを予定。

署名
----
KabuSys チーム
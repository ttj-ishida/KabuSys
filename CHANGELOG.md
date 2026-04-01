CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-04-01
------------------

Added
- 初回リリース。パッケージ kabusys のコア機能を追加。
- パッケージ初期化:
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" と公開サブパッケージの __all__ を定義（data, strategy, execution, monitoring）。
- 環境設定管理:
  - src/kabusys/config.py
    - .env ファイルおよび環境変数からの設定読込機能を実装。
    - プロジェクトルート自動検出 (_find_project_root): .git または pyproject.toml を起点に検索（CWD に依存しない実装）。
    - .env パーサー (_parse_env_line): コメント行、export 構文、シングル/ダブルクォート内のエスケープ処理、行内コメントの取り扱いなどに対応する堅牢なパース実装。
    - .env ファイル読み込み (_load_env_file): OS 環境変数保護（protected set）と override ロジック、読み込み失敗時の警告出力。
    - 自動ロードの制御: KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
    - Settings クラス: J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / ログレベル / 環境（development/paper_trading/live）等のプロパティを提供。必須変数未設定時は明示的に ValueError を発生させる。
- AI ニュース NLP / レジーム判定:
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を基にニュースを銘柄単位に集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを ai_scores テーブルに書き込む処理を実装。
    - バッチサイズ、文字数/記事数トリム、429/ネットワーク/タイムアウト/5xx のリトライ（指数バックオフ）、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の保護（書き込み前に対象コードのみ DELETE → INSERT）などの堅牢な設計。
    - calc_news_window により JST ベースのニュース収集ウィンドウ（前日 15:00 ～ 当日 08:30）を UTC naive datetime で返すユーティリティを実装。
    - テスト容易性のため _call_openai_api を patch 可能にし、JSON パース時に余計な前後テキストが混入した場合の復元ロジック（最外の { } を抽出）を実装。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）と、ニュース由来のマクロセンチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等的に書き込む処理を実装。
    - OpenAI 呼び出しのリトライ・バックオフ、API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフ設計、レスポンス JSON の安全なパースなどを実装。
    - レジーム合成の閾値・重み・モデル（gpt-4o-mini）がコード内定義されている（調整可能）。
- データ基盤関連:
  - src/kabusys/data/calendar_management.py
    - JPX（市場）カレンダー管理。market_calendar テーブルの夜間差分更新ジョブ（calendar_update_job）と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB 登録データ優先、未登録日は曜日ベース（週末除外）でフォールバックする一貫した設計。バックフィル・先読み・健全性チェックを実装。
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL パイプラインの骨組みを実装。差分取得、idempotent な保存（jquants_client 経由）、品質チェックの枠組みを用意。
    - ETLResult dataclass を定義（src/kabusys/data/pipeline.py）し、etl モジュールから再エクスポート（src/kabusys/data/etl.py）。
    - ETLResult は品質チェック結果・エラー一覧・保存件数などを保持し、辞書化機能を提供。
- 研究（Research）モジュール:
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ（ATR/出来高/売買代金）、バリュー（PER/ROE）などのファクター計算を実装。DuckDB 上で SQL を組み合わせて計算し、(date, code) キーの dict リストを返す設計。
    - 欠損データやデータ不足時の None ハンドリング、ログ出力を備える。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、Spearman ランク相関による IC 計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
  - src/kabusys/research/__init__.py で主要関数を公開（zscore_normalize を data.stats から re-export）。
- その他ユーティリティ・設計:
  - DuckDB をデータストア前提とした SQL 実装が多用されている（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等のテーブルを参照）。
  - トランザクション制御（BEGIN / DELETE / INSERT / COMMIT）と例外時の ROLLBACK 守備を各所で採用。ROLLBACK 失敗時は警告ログを出力して上位に例外を伝播。
  - ログ出力を重視し、処理の段階・件数・失敗理由を詳細に記録する実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 環境変数による API キー取得（OpenAI / J-Quants 等）の実装。必須項目未設定時は明確な例外（ValueError）で失敗させるため、秘密情報の未設定が黙って続行されるリスクを低減。

Notes / Implementation details
- OpenAI 関連:
  - 使用モデル: gpt-4o-mini（JSON mode を使用し厳密な JSON 出力を期待）。
  - レスポンスの堅牢なパースとバリデーションを実装。API エラー（5xx 等）や RateLimit/ネットワーク障害はリトライ、その他はスキップしてフェイルセーフにフォールバック。
  - テスト容易化のため _call_openai_api を patch 可能に実装（ユニットテストでモック化しやすい）。
- 日付扱い:
  - すべてのコア処理は datetime.today()/date.today() を直接参照しない方針（ルックアヘッドバイアス防止）。各関数は target_date を引数として受け取り deterministically に処理する。
- DuckDB の互換性注意:
  - executemany に空リストを渡せないバージョンを考慮して、事前に空チェックを行っている箇所がある。

Acknowledgements
- 初回リリース。今後の改善点（ドキュメント強化、API キーのセキュアな管理、追加ユニットテスト、CI/CD など）を計画しています。

--- 
（注）この CHANGELOG は提供されたコード内容から推測して作成しています。実際のリリースノート作成時はコミット履歴・PR・Issue 情報を参照して補完してください。
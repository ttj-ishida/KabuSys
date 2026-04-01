Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ に準拠して記録します。

[Unreleased]
------------

- （現在なし）

[0.1.0] - 2026-04-01
-------------------

Added
- 初期リリース。日本株自動売買・データプラットフォームのコア機能を追加。
  - パッケージ初期化:
    - kabusys.__version__ = 0.1.0 を設定。
    - 公開モジュール一覧を定義 (data, strategy, execution, monitoring)。
  - 設定管理 (kabusys.config):
    - .env ファイルおよび環境変数から設定を読み込む自動ロード実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索する _find_project_root を実装。これにより CWD に依存しない自動ロードを実現。
    - .env パーサ実装: export KEY=val 形式、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメントの取り扱い等に対応する堅牢な _parse_env_line を実装。
    - .env 読み込み順序: OS 環境 > .env.local（上書き）> .env（初期設定）。OS 環境変数は protected として上書きされない仕様。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB /監視 / システム設定等のプロパティを環境変数から取得。未設定の必須変数は ValueError で明示的に失敗する。
    - 環境値検証: KABUSYS_ENV（development|paper_trading|live）や LOG_LEVEL のバリデーションを実装。
  - AI モジュール (kabusys.ai):
    - news_nlp.score_news:
      - raw_news と news_symbols を集約し、銘柄ごとに最大 _MAX_ARTICLES_PER_STOCK（10）・最大文字数 _MAX_CHARS_PER_STOCK（3000）でプロンプトを作成。
      - OpenAI gpt-4o-mini（JSON Mode）を用いたバッチ処理。1 API 呼び出しあたり最大 _BATCH_SIZE（20）銘柄。
      - 429 / 接続断 / タイムアウト / 5xx に対する指数バックオフでのリトライ（最大回数 _MAX_RETRIES）。
      - レスポンスの厳密なバリデーション（results 配列・code/score の存在・数値性・既知コードのみ受け入れ）を行い、スコアを ±1.0 にクリップして ai_scores テーブルへ冪等的に保存（DELETE → INSERT）。
      - タイムウィンドウ計算 calc_news_window を提供（JST基準: 前日15:00〜当日08:30 を UTC に変換して比較）。
      - API キー注入可能（引数 api_key または環境変数 OPENAI_API_KEY）。
      - API 失敗時は個別チャンクをスキップし、全体処理を継続するフェイルセーフ設計。
    - regime_detector.score_regime:
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
      - ma200_ratio の計算（target_date 未満のデータのみを使用してルックアヘッドバイアスを防止）。
      - raw_news からマクロ関連キーワードでフィルタしてタイトルを抽出し、LLM によりマクロセンチメントを JSON で取得。API 失敗は macro_sentiment=0.0 にフォールバック。
      - スコア合成後に market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - Data モジュール (kabusys.data):
    - calendar_management:
      - market_calendar を基にした営業日判定ロジックを実装（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
      - DB にデータがない場合は曜日（平日）ベースのフォールバックを採用。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を更新する夜間バッチ処理。バックフィルと健全性チェック（未来日付の閾値）を実装。
    - pipeline / ETL:
      - ETLResult dataclass を公開し、ETL 実行結果・品質チェック結果・エラー情報を一元管理できる構造を提供。
      - 差分更新、バックフィル、品質チェックの設計方針をコードに反映。
    - etl.py で pipeline.ETLResult を再エクスポート。
  - Research モジュール (kabusys.research):
    - factor_research:
      - calc_momentum: mom_1m/3m/6m、ma200_dev の計算を実装（DuckDB 上のウィンドウ関数を活用）。
      - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials から直近財務を取得して PER / ROE を計算（EPS=0または欠損時は None）。
    - feature_exploration:
      - calc_forward_returns: 将来リターン計算（複数ホライズンに対応、horizons のバリデーションあり）。
      - calc_ic: Spearman ランク相関（IC）を実装。データ不足（有効レコード < 3）では None を返す。
      - rank: 同順位は平均ランクを返す実装（丸めで ties の検出安定化）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - 研究向け関数は全て DuckDB 接続を受け取り、外部 API や取引実行には影響しない設計。
  - その他:
    - ロギング、警告、フェイルセーフの一貫した扱い（API 失敗時のログ出力と代替値の使用）。
    - テスト容易性を考慮した設計（OpenAI 呼び出しのラッパー関数は unittest.mock で差し替え可能に実装）。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- 環境変数扱いの注意点: OS 環境変数を保護するため .env の上書きに protected キーセットを導入。自動ロードを不要な環境で無効化するフラグを用意。

Deprecated
- なし。

Removed
- なし。

Known issues / TODO
- pipeline._get_max_date の末尾が未完成（return date.fro のような未完了の記述が存在）。この状態では構文エラーまたは未定義の動作を引き起こす可能性があるため、実稼働前に修正が必要。
- 一部関数の外部依存（jquants_client, kabuysys.data.jquants_client 等）は実行環境でのモック/実装が必要（テスト・デプロイ時の注意）。
- OpenAI や J-Quants API 呼び出しは外部サービスへの接続が必要であり、API キーやネットワーク設定が必須。

Notes
- ルックアヘッドバイアス防止: AI 関連・研究関連の関数群は内部で datetime.today() や date.today() を参照せず、外部から渡された target_date に基づいて処理を行うように設計されています。バックテストや研究用途での安全性が考慮されています。
- DuckDB をベースにした SQL と Python の組合せでデータ処理を実装しており、executemany の空リストに関する互換性注意（コード内に回避ロジックあり）。
- ローカル環境向け .env の取り扱いは柔軟に設計されていますが、本番環境では OS 環境変数（または安全なシークレット管理）を推奨します。

貢献・バグ報告
- 不具合や改善提案がある場合は issue を作成してください。特に pipeline._get_max_date の未完了箇所は早期対応を推奨します。
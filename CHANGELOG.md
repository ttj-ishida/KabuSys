CHANGELOG
=========

すべての注目すべき変更履歴をここに記録します。
このプロジェクトはセマンティックバージョニングに従います: MAJOR.MINOR.PATCH

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初回リリース: kabusys 0.1.0
  - パッケージメタ情報:
    - バージョン: src/kabusys/__init__.py の __version__ = "0.1.0"
    - __all__ に data, strategy, execution, monitoring を公開

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイル（.env, .env.local）およびOS環境変数から設定を自動ロードする機能を実装
    - プロジェクトルート判定は .git または pyproject.toml を起点に行い、CWD に依存しない実装
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
    - .env のパースは export KEY=val, クォート（シングル/ダブル）のエスケープ、行末コメント取り扱いなどに対応
    - .env.local は .env を上書き（既存 OS 環境変数は保護）
  - Settings クラスを提供（settings インスタンス）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック関数を含む
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）を Path として取得
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の値検証
    - is_live / is_paper / is_dev ヘルパー

- ニュース NLP（AI） (src/kabusys/ai/news_nlp.py)
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを評価する score_news を実装
    - ニュース時間ウィンドウの計算: 前日15:00 JST ～ 当日08:30 JST（UTC 変換を内部で行う calc_news_window）
    - 1銘柄あたり最大記事数・文字数のトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
    - バッチ処理（1回のAPIコールで最大 20 銘柄）で効率化
    - 429 / ネットワーク断 / タイムアウト / 5xx サーバーエラーに対する指数バックオフ・リトライ実装
    - レスポンスは厳密な JSON を期待しつつ、余分な前後テキストが混入した場合の復元（最外側の {} 抽出）に対応
    - レスポンス検証: results 配列・code/score の存在・既知コードのみ採用・数値検証・±1.0 クリップ
    - DuckDB への書き込みは部分置換（DELETE → INSERT）で冪等性と部分成功時の保護を実現
    - テスト容易性: _call_openai_api をモジュール内で定義して unittest.mock.patch により差し替え可能

- 市場レジーム判定（AI） (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム判定（score_regime）を実装
    - ma200_ratio は prices_daily から target_date 未満のデータのみを参照しルックアヘッドを防止
    - マクロニュースは news_nlp.calc_news_window を用いてウィンドウ抽出し、OpenAI で macro_sentiment を算出（記事無し時は呼び出さない）
    - OpenAI 呼び出しは独立した実装（news_nlp とプライベート関数を共有しない設計）
    - LLM の失敗時は macro_sentiment=0.0（フェイルセーフ）
    - 合成後の regime_score を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - OpenAI 呼び出し時のリトライ・エラーハンドリングを含む（RateLimit, Timeout, APIError の 5xx 判定など）

- データ基盤ユーティリティ (src/kabusys/data/*)
  - カレンダー管理 (calendar_management.py)
    - market_calendar テーブルを使った営業日判定ユーティリティを実装
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録データ優先、未登録日は曜日ベースでフォールバックする一貫したロジック
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・健全性チェック含む）
    - DB が未取得の場合に安全に動作するフォールバックと最大探索日数制限を実装
  - ETL パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを公開（etl.py で再エクスポート）
      - 取得件数、保存件数、品質チェック結果、エラー一覧等を保持
      - has_errors / has_quality_errors / to_dict を実装
    - 差分取得、backfill、DuckDB の最大日付取得等のヘルパーを実装
    - quality モジュールとの連携設計（重大度を扱う）

- 研究用モジュール (src/kabusys/research/*)
  - factor_research.py
    - モメンタム（1M/3M/6M リターン）、200 日 MA 乖離、ATR（20日）、流動性（20日平均）等のファクター計算関数を実装
      - calc_momentum, calc_volatility, calc_value
    - DuckDB を用いた窓関数中心の実装、データ不足時は None を返す扱い
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、入力検証あり）
    - IC（Spearman の ρ）計算 calc_ic（ランク相関）
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸めで ties 対策）
    - 統計サマリー関数 factor_summary（count/mean/std/min/max/median）
  - research パッケージ __init__ で主要関数をエクスポート

- 公開 API / 設計共通事項
  - DuckDB を一貫して使用する設計（関数は DuckDB 接続を受け取り SQL + Python で処理）
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を内部で参照しない設計（入力として target_date を受け取る）
  - OpenAI 呼び出しに対して堅牢なリトライ・バックオフ・パースフォールバックを実装
  - DB 書き込みは冪等（DELETE → INSERT、ON CONFLICT 等を想定）で安全に実行
  - テスト容易性のため一部内部API呼び出しは差し替え可能に実装

Security
- 環境変数に API キーを要求する箇所があるため、運用時は秘密情報管理に注意
  - OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_* 等

Known issues / 注意事項
- OpenAI との通信失敗時は多くの処理でフォールバック（0.0 スコアやスキップ）して継続する設計だが、
  運用監視（ログ/アラート）を併用することを推奨
- DuckDB executemany は空リストに対する制約があるため、コード内で空チェックを行っている点に注意
- strategy / execution / monitoring パッケージは __all__ で公開されているが、本リリースに含まれる実装は上記のデータ・研究・AI 周りが中心



- 以上が初回リリース 0.1.0 の主な追加点です。今後のリリースではテストカバレッジ強化、運用向け監視/アラート、strategy / execution / monitoring 周りの機能拡充を予定しています。
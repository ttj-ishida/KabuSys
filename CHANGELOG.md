Keep a Changelog
=================

すべての注目すべき変更を（バージョン履歴として）このファイルに記載します。  
このプロジェクトは Keep a Changelog の方針に準拠しています。  

0.1.0 - 2026-03-28
------------------

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装した最初の公開版です。

Added
- パッケージ基盤
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を追加。
  - kabusys.__all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定 / ロード
  - src/kabusys/config.py
    - .env ファイル（および .env.local）または OS 環境変数から設定を自動的に読み込む仕組みを実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に探索するため、CWD に依存しない動作。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用フック）。
    - .env パーサ実装:
      - export KEY=val 形式に対応。
      - シングル/ダブルクォートの中でのバックスラッシュエスケープを考慮。
      - クォートなしの行におけるインラインコメント処理（直前が空白/タブの場合のみ）。
    - 環境値取得ユーティリティ Settings を提供（必須変数未設定時は ValueError を送出）。
    - 主要設定プロパティ例:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須チェック。
      - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値。
      - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証、 is_live / is_paper / is_dev のユーティリティ。

- AI: ニュース NLP とレジーム検出
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini, JSON mode）でセンチメント（-1.0〜1.0）を評価。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換ロジックを提供する calc_news_window）。
    - バッチ処理: 最大 _BATCH_SIZE（20）銘柄を一度に送信、1銘柄あたりの記事は件数（10）・文字数（3000）で制限。
    - 再試行戦略: 429 / ネットワークエラー / タイムアウト / 5xx に対して指数バックオフでリトライ（デフォルト _MAX_RETRIES=3）。
    - レスポンス検証: JSON の構造・型検証（results 配列、code と score 等）、不正レスポンスはログ出力してスキップ。
    - 書き込み: 成功した銘柄のみ ai_scores テーブルへ（DELETE→INSERT の冪等パターン）。DuckDB の executemany の仕様を考慮して空パラメータは回避。
    - テスト容易性: _call_openai_api をモック差替え可能。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタし、最大 20 記事を LLM に渡す。LLM 失敗時は macro_sentiment = 0.0 でフェイルセーフ継続。
    - レジームスコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。閾値でラベル化（_BULL_THRESHOLD/_BEAR_THRESHOLD）。
    - DB 書き込みはトランザクションで冪等に実施（BEGIN/DELETE/INSERT/COMMIT）。エラー時は ROLLBACK を試行し例外を上位へ伝播。
    - OpenAI 呼び出しは news_nlp とは切り離した独立実装でモジュール結合を低減。

- Data（データ基盤）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダーの管理と営業日ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - market_calendar が未取得のときは曜日ベースのフォールバック（土日を休業日扱い）。
    - next/prev_trading_day は DB の登録値を優先し、未登録日は曜日フォールバックで処理。最大探索日数 (_MAX_SEARCH_DAYS) を設け無限ループを回避。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に保存。バックフィル／健全性チェックを実装。
    - DB からの date 取り扱いに注意（全て date オブジェクトで扱う）。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基盤実装。
    - 差分取得、保存（jquants_client との連携）、品質チェック（quality モジュール）を想定。
    - ETLResult データクラスを導入（target_date／取得件数／保存件数／quality_issues／errors 等を保持）。has_errors / has_quality_errors / to_dict メソッドを提供。
    - 内部ユーティリティ: テーブル存在確認、テーブルの最大日付取得などを実装。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポートする公開インターフェース。

- Research（リサーチユーティリティ）
  - src/kabusys/research/factor_research.py
    - ファクター計算（モメンタム・ボラティリティ・バリュー）を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
      - calc_volatility: 20 日 ATR（avg true range）、相対 ATR、20 日平均売買代金、出来高比率等。
      - calc_value: raw_financials から最新財務（target_date 以前）を取得して PER/ROE を計算。
    - DuckDB の SQL ウィンドウ関数を活用し、営業日ベースのラグを計算。全関数は prices_daily / raw_financials のみ参照。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満なら None を返す。
    - rank: 同順位は平均ランクとするランク付けユーティリティ（round により ties の誤差対策）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出する統計サマリー関数。
  - src/kabusys/research/__init__.py で主要関数をエクスポート（zscore_normalize は data.stats から）。

Changed
- （初回リリースのため変更は無し）

Fixed
- （初回リリースのため修正は無し）

Notes / 設計上の重要ポイント
- ルックアヘッドバイアス防止:
  - news_nlp と regime_detector では内部で datetime.today()/date.today() を直接参照しない。すべての処理に target_date を明示的に渡す設計。
  - prices_daily クエリは target_date 未満／間の条件を明確にして将来データ参照を防止。
- フェイルセーフ:
  - LLM 呼び出し失敗時は例外で処理を止めず、適切なデフォルト（例: macro_sentiment=0.0）で継続しログ記録する方針。
  - DB 書き込みはトランザクションで冪等性を担保し、部分失敗が他データを毀損しないよう配慮。
- テスト性:
  - OpenAI 呼び出しを行う内部関数（_call_openai_api）を明示的に分離しており、unittest.mock.patch による差し替えが容易。

今後の予定（例）
- strategy / execution / monitoring の実装強化（現状はパッケージ公開のみ）。
- jquants_client の統合テスト、ETL のスケジューリング・監査ログの追加。
- モデル評価（IC の長期集計・バックテスト連携）や Slack 通知等のオペレーション機能追加。

Contributing
- バグや改善提案は issue を立ててください。プルリクエストは開発ブランチへどうぞ。

ライセンス
- （このファイルでは明記していません。プロジェクトルートの LICENSE を参照してください。）
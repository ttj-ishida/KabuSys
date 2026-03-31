CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
初回リリース v0.1.0 のコードベースから推測した機能追加・設計意図・既知の制約を日本語でまとめています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース "KabuSys"（src/kabusys）
  - 公開モジュール群: data, research, ai, （strategy, execution, monitoring を __all__ に含むが一部実装は別途）。
  - バージョン: 0.1.0

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイルや環境変数から設定を読み込む自動ロードを実装。
    - プロジェクトルート特定ロジック: 現ファイル位置から親ディレクトリを探索し .git または pyproject.toml を検出してルートを決定（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local（override）> .env（override=False）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - OS の既存環境変数を保護する protected ロジックを実装。
  - 行パーサーを堅牢化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォート外でのみ # をコメントとして扱う）など。
  - Settings クラスを提供（settings インスタンスで使用可能）。
    - J-Quants / kabuステーション / Slack / データベースパス / 監視閾値 / システム環境（KABUSYS_ENV）/ ログレベル等のプロパティを用意。
    - 必須値未設定時は _require を通して ValueError を返す。
    - env/log_level の値検証（許容値セット）と便利プロパティ is_live / is_paper / is_dev を提供。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news からニュースを収集して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores に書き込む機能を実装。
    - calc_news_window: タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST に対応する UTC 範囲）を計算。
    - score_news: 銘柄ごとに記事を集約し（最大記事数・文字数トリム）、最大 20 銘柄毎のバッチで LLM に送信しスコアを取得。
    - バッチ処理: _BATCH_SIZE=20、1銘柄あたり最大 _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK を設定。
    - API 呼び出しでの堅牢性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、その他のエラーはスキップして継続（フェイルセーフ）。
    - レスポンス検証: JSON 解析の頑健化（前後余計テキストの復元）、"results" 構造の型チェック、未知コードの無視、数値検査、±1.0 のクリッピング。
    - DB 書き込みは冪等化: 書き込み対象コードのみ DELETE → INSERT（DuckDB executemany の制約に配慮）。
    - テスト容易性: _call_openai_api をモック差し替え可能に設計。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む機能を実装。
    - _calc_ma200_ratio: target_date 未満のデータのみ使用して MA200 乖離を算出。データ不足時は中立 (1.0) を返す。
    - _fetch_macro_news: マクロキーワード群で raw_news のタイトルを抽出（最大件数制限）。
    - _score_macro: OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を算出。API エラー時は 0.0 にフォールバック。リトライ/バックオフ実装あり。
    - score_regime: API キー解決、MA 計算、ニュース取得、LLM 評価、スコア合成、閾値判定、冪等 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照せず、prices_daily クエリに date < target_date の排他条件を適用。

- 研究（Research）モジュール（src/kabusys/research/*.py）
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日 MA 乖離）を DuckDB SQL ウィンドウ関数で算出。データ不足は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS が 0/欠損時は None）。
    - 設計方針: DuckDB のみ参照し本番注文 API 等にはアクセスしない。結果は (date, code) をキーとする dict のリストで返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD によりまとめて取得。ホライズン検証（1..252）あり。
    - calc_ic: スピアマン順位相関（ランクの Pearson）で IC を計算。十分なサンプルがない場合は None を返す。
    - rank: 同順位は平均ランクにする安定した順位付け実装（小数丸めを含む）。
    - factor_summary: count/mean/std/min/max/median の統計要約を計算。

- データ管理 / ETL / カレンダー（src/kabusys/data/*.py）
  - calendar_management:
    - market_calendar を使った営業日判定ロジックと夜間バッチ更新ジョブ（calendar_update_job）を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック。最大探索日数を制限して無限ループを防止。バックフィル・健全性チェックを実装。
    - calendar_update_job は jquants_client を用いて差分取得 → 保存（冪等）し、取得結果件数を返す（エラー時は 0）。
  - pipeline (ETL):
    - ETLResult データクラスを定義し、ETL の成果（取得/保存レコード数、品質問題、エラー）を集約。
    - ETL の設計方針（差分更新、バックフィル、品質チェックの収集を行う）をコードコメントで明示。
    - data/etl は ETLResult を再エクスポート。
  - DuckDB を主要な計算・保存基盤として広く利用。

Security
- 特記事項なし（初期実装）。ただし環境変数に API キー等を期待するため、運用時は .env 管理・権限管理に注意。

Known Issues / Limitations
- pipeline._get_max_date の末尾がソース中で途中までしか表示されておらず（"return date.fro" で切れている）、ファイル断片のため実装が未完または誤って切れている可能性があります。実運用前に該当箇所の完全な実装確認が必要です。
- __all__ に strategy / execution / monitoring が含まれているが、提示されたコード中ではこれらのモジュール実装が含まれていないため、別ファイルでの実装または今後の追加が想定されます。
- OpenAI API の利用は gpt-4o-mini を想定しているため、実利用時は利用規約・コスト・API のバージョン違いに注意する必要があります。
- DuckDB executemany に空リストが指定できない等の互換性考慮が存在するため、DuckDB のバージョンに依存する挙動に注意（コード内に既知のワークアラウンドあり）。

Notes / Implementation Highlights
- ルックアヘッドバイアス対策が各 AI/研究モジュールの設計で優先的に扱われている（datetime.today()/date.today() を直接参照しない、SQL クエリで排他条件を付与）。
- DB 書き込みは冪等化を重視（DELETE → INSERT の明示操作、BEGIN/COMMIT/ROLLBACK によるトランザクション制御）。
- OpenAI 呼び出しについてはテストのために内部呼び出し関数をモック置換できるようにしている（テストしやすい設計）。
- エラー時のフェイルセーフ方針: LLM/API の失敗はスコアを 0 にフォールバックする、または該当チャンクをスキップして処理を継続（部分的なデータ消失を避ける）。

Migration / Upgrade notes
- 初回リリースのためマイグレーションはなし。次版では pipeline の未完箇所修正、strategy/execution/monitoring の追加実装、テスト・ドキュメントの整備が想定されます。

以上がソースコードから推測して作成した CHANGELOG (Keep a Changelog 準拠) です。追加で日付・リリースノートの細分化や、未実装箇所の修正案を作成することも可能です。必要であれば指示してください。
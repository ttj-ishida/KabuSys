CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠し、セマンティックバージョニングを採用しています。
（コードベースの内容から実装状況・設計方針を推測して記載しています）

Unreleased
----------

- （なし）

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を公開。主要サブパッケージとして data, research, ai 等を想定。
- 環境設定/ローダー (src/kabusys/config.py)
  - .env/.env.local の自動読み込み（プロジェクトルートの検出は .git または pyproject.toml に基づく）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサーの実装: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントルール等に対応。
  - 環境変数取得用 Settings クラスを提供（J-Quants, kabu API, LINE, DB パス, 監視設定, システム設定など）。必須キー不在時は明確な ValueError を送出。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約し、銘柄毎にニューステキストを結合して OpenAI（gpt-4o-mini）の JSON Mode でセンチメントを取得する機能を実装。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数上限／文字数上限（トリム）を備える。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで行う。API の失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
    - レスポンス検証ロジックを実装（JSON 抽出、results リスト・code/score 検証、スコアの数値性/有限性チェック、スコアの ±1.0 クリップ）。
    - DuckDB への書き込みは部分置換（対象 code の DELETE → INSERT）で冪等性と部分失敗時の既存データ保護を担保。
    - テストの容易化: _call_openai_api を patch してモック可能。
    - 公開 API: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - prices_daily と raw_news を参照、OpenAI を用いたマクロセンチメント評価（記事が無ければ LLM 呼び出しをスキップし macro_sentiment=0.0）。
    - API リトライ・バックオフ、レスポンス JSON パース失敗時のフォールバック、DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）および ROLLBACK 保護。
    - テストの容易化: news_nlp とは別実装の _call_openai_api を用意し patch 可能。
    - 公開 API: score_regime(conn, target_date, api_key=None)
- データ基盤モジュール (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - 夜間バッチ更新 job (calendar_update_job) を実装。J-Quants クライアント経由で差分取得し冪等保存、バックフィルと健全性チェックを実装。
  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスで ETL 実行結果を集約（取得数・保存数・品質問題・エラー等）。
    - 差分更新、backfill、品質チェック（quality モジュール想定）を行う設計方針を明記。
    - jquants_client の save_* を使った冪等保存を想定。
- 研究（Research）モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M）、200日移動平均乖離、ATR、流動性（20日平均売買代金・出来高比）等の計算関数を実装。
    - DuckDB を直接クエリして結果を (date, code) ベースの dict リストで返す。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターンの計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB クエリで実装。
- ロギング・監視関連
  - 各モジュールで詳細な logger 呼び出しを追加（info/warning/debug）し、失敗時の理由やフォールバック動作をログに記録。

Changed
- （初回リリースのため「変更」はなし。設計上の注意点・制約をドキュメントに反映）
  - DuckDB executemany の空リスト制約に対応した実装（空チェックをしてから executemany を呼ぶ）。
  - API レスポンスパースに対する耐性強化（JSON 前後の余計な文字列を削る復元処理など）。
  - 日付取り扱いはすべて datetime.date / datetime に統一しタイムゾーンの混入を防止する方針を明記。

Fixed
- （初版リリースのため「修正履歴」はなし。ただし多くのエラーケースでフェイルセーフ処理を実装）
  - OpenAI 呼び出し失敗時のフォールバック（スコア 0.0、チャンクスキップ等）により全体処理が停止しないよう改良。
  - DB 書き込み中に例外発生した場合の ROLLBACK とログ出力を追加。

Security
- OpenAI API キーが未設定の場合は明確な ValueError を送出する実装（score_news / score_regime）。
- .env ロード時に OS 環境変数を保護する仕組み（protected set）を実装。

Notes / Implementation details
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON Mode を利用する設計。レスポンスの厳密な JSON 出力を期待するが、パース失敗時は復元を試みて安全にスキップする。
- ルックアヘッドバイアス防止のため、内部実装では datetime.today() や date.today() を直接参照しない設計（関数呼び出し側が target_date を明示的に渡す）。
- DB 書き込みは可能な限り冪等性を担保（DELETE→INSERT、ON CONFLICT 想定）し、部分失敗時に既存データを保護する。
- テスト容易性のため、API 呼び出し箇所は patch 可能に実装（ユニットテストで置換しやすい設計）。

Breaking Changes
- なし（初回リリース）

Contributing
- バグ報告・機能提案は Issue を通じてお願いします。ユニットテストで OpenAI 呼び出しをモックするパターンが想定されています（_call_openai_api の patch 等）。

以上。コード内のログメッセージや docstring に基づいて主な機能と設計上の注意点をまとめました。追加で日付別の細かなリリース履歴／履歴を分割したい場合は、変更履歴の粒度（AI, Data, Research など）に応じてバージョンを分けて記載できます。
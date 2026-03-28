Keep a Changelog
=================
すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

[Unreleased]
-------------

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初期リリース: KabuSys 日本株自動売買システムのコア実装を追加。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは既存の OS 環境変数から設定を自動読み込みする機能を実装。
  - .env のパースは export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロード無効化用 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト向け）。
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）をプロパティで取得。env / log_level のバリデーションを実装。
- AI モジュール
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄毎にニュースを纏め、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、記事数上限、文字数トリム、JSON モードのレスポンス検証、スコア ±1.0 のクリップ、リトライ（429/ネットワーク/5xx 用の指数バックオフ）を実装。
    - DuckDB の executemany 空リスト制約を考慮した安全な書き込み（DELETE→INSERT の部分更新）を実装。
    - テスト容易性のため _call_openai_api を patch 可能に実装。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算ユーティリティを提供。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - マクロニュース抽出、OpenAI 呼び出し、リトライ処理、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を含むフローを実装。
    - LLM 呼び出しは失敗時は macro_sentiment=0.0 としてフェイルセーフで継続する設計。
  - ai パッケージ公開インターフェース: score_news, score_regime をエクスポート。
- データプラットフォーム関連 (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し market_calendar テーブルに冪等保存。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。DB にデータがない日については曜日ベースでフォールバックする一貫した挙動を提供。
    - バックフィル、先読み、最大探索日数、健全性チェック（極端に将来の last_date をスキップ）等の安全対策を実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETL の結果を表す dataclass ETLResult を実装（取得/保存件数、品質チェック結果、エラー一覧等）。
    - パイプライン側のユーティリティ（差分取得、最大日付取得、テーブル存在チェック等）を実装。
    - etl モジュールから ETLResult を再エクスポート。
- 研究（Research）モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を DuckDB 経由で計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新の財務指標を取得し PER/ROE を計算。
    - 実行は DB（prices_daily / raw_financials）オンリーで外部 API を呼ばない設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得する汎用実装（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）を計算する実装（欠損・同値処理対応）。
    - rank, factor_summary: ランク化・統計サマリーユーティリティを実装。
  - research パッケージ公開インターフェースを整備（主要関数を __all__ でエクスポート）。
- 設計方針・安全対策（全体）
  - ルックアヘッドバイアス防止のため、各モジュールは datetime.today()/date.today() を直接参照しない（score_regime/score_news 等は target_date を引数で受ける）。
  - LLM 呼び出しの失敗はフェイルセーフ（デフォルト中立スコア）で処理を継続する設計。
  - DB 書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT の想定）して実装。
  - OpenAI 呼び出しのレスポンスパースは堅牢化（JSON 部分抽出など）。
  - テスト容易性を考慮した差し替えポイント（_call_openai_api の patchable 実装、KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加。

Fixed
- DuckDB executemany に対する空リストバインドの互換性問題を考慮し、空リストのときは実行をスキップする安全処理を追加（ai/news_nlp, ai/regime_detector, data/pipeline の書き込みロジック）。
- データ不足時の挙動を明示（ma200 のデータ不足時は中立 1.0 を返し WARNING をログ出力）。
- OpenAI レスポンスの JSON パース失敗時に余計な前後テキストが混ざるケースを補正して復元を試みる処理を追加。

Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で必須。未設定時は ValueError を送出して明示的に失敗させる実装。
- .env 自動読み込み時に既存 OS 環境変数を保護するため protected セットを導入し、意図しない上書きを防止。

Notes / For developers
- OpenAI クライアント呼び出し箇所はテスト時に差し替えやすくなっています（unittest.mock.patch で _call_openai_api を置換可能）。
- J-Quants クライアント呼び出しは kabusys.data.jquants_client を経由する想定（実際の fetch/save 実装はクライアント側に委譲）。
- 各モジュールは「DB のみ参照」ポリシーを基本とし、本番の発注・実行ロジック（kabu API 等）とは分離されています。

Acknowledgements
- 本リリースは初期実装のため、今後の運用で得られた知見に基づく改善（性能チューニング、追加ロギング、より厳密な品質チェック等）を予定しています。
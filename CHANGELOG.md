CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" とセマンティックバージョニングに準拠します。

v0.1.0 - 2026-03-29
-------------------

初回リリース。以下の主要機能・実装が追加されました。

Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0 を追加（src/kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ としてエクスポート。

- 設定管理
  - .env ファイルおよび環境変数読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から自動検出し、.env / .env.local を読み込む自動ロードを実装。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応した堅牢な実装。
    - .env.local は .env の上書き（override=True）として扱い、OS 環境変数（起動時の os.environ）で保護されたキーは上書きしない。
    - 必須環境変数未設定時に ValueError を送出する _require ヘルパーと Settings クラスを追加。
    - Settings に J-Quants / kabu API / Slack / DB パス / 実行環境 (development/paper_trading/live) / LOG_LEVEL の検証ロジックを実装。

- データ関連
  - ETL インターフェース: ETLResult を公開（src/kabusys/data/etl.py, pipeline.py）。
    - ETLResult: ETL 実行結果の dataclass（取得数、保存数、品質問題、エラー等を含む）。
  - ETL パイプライン (概要実装): 差分取得、バックフィル、品質チェック、DuckDB 最大日付取得等のユーティリティ（src/kabusys/data/pipeline.py）。
    - DuckDB テーブル存在チェック、最大日付取得ヘルパーを追加。
    - デフォルトのバックフィル日数 / カレンダー先読み等の定数を定義。
  - マーケットカレンダー管理モジュールを追加（src/kabusys/data/calendar_management.py）。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days の営業日判定ロジック。
    - market_calendar が未取得の場合は曜日ベース（土日を休日）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新するバッチ処理。
    - ロバストネス: 最大探索日数制限、バックフィル、健全性チェック（将来日付の異常検出）を実装。
    - jquants_client 経由の fetch/save 呼び出しに対する例外ハンドリングとログ出力。

- 研究・因子計算
  - research パッケージの初期実装（src/kabusys/research/）。
    - factor_research.py:
      - モメンタム: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）算出機能（calc_momentum）。
      - ボラティリティ/流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率（calc_volatility）。
      - バリュー: EPS を用いた PER、ROE の取得（raw_financials と prices_daily の組合せ、calc_value）。
      - 各関数は DuckDB の SQL ウィンドウ関数を利用し date / code をキーとした結果リストを返す。
    - feature_exploration.py:
      - 将来リターン計算（calc_forward_returns）：指定ホライズンの LEAD を用いた一括取得。
      - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関（内部で rank を実装）。
      - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）。
      - rank ユーティリティ: 同順位は平均順位として扱う実装、丸めで ties の誤差を抑制。
    - research パッケージは外部依存を最小化し、主に DuckDB と標準ライブラリで実装。

- AI（NLP/LLM）機能
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）。
    - raw_news と news_symbols を集約して銘柄ごとにニュースを合成し、OpenAI（gpt-4o-mini）に JSON モードでバッチ送信して銘柄別センチメントを取得。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で厳密に計算（UTC naive datetime を返す）。
    - チャンク処理（1 コール最大 20 銘柄）、1 銘柄あたり最大記事数・最大文字数でトリム。
    - リトライ: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ。
    - レスポンスのバリデーション (_validate_and_extract): JSON 抽出耐性（前後の余計なテキストを許容）、results 配列の検査、未知コードの無視、スコアの数値変換と ±1.0 クリップ。
    - DuckDB の executemany の互換性を考慮し、DELETE/INSERT は個別実行や空リストチェックを行う。
    - API キー注入可能（api_key 引数）でテスト容易性を確保。未設定時は ValueError を送出。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）。
    - ETF 1321（日経225 連動型）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタしてタイトルを抽出、LLM（gpt-4o-mini）に投げて macro_sentiment を算出。
    - LLM 呼び出しの再試行・フォールバック（API 失敗時は 0.0）およびレスポンスの JSON パース耐性を実装。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。失敗時は ROLLBACK を試行し、ログを出力して例外伝播。
    - date.today() 等の直接参照は避け、ルックアヘッドバイアスを防止する設計。

Changed
- DuckDB 互換性向上
  - executemany に空リストを渡した場合の挙動（DuckDB 0.10 の制約）に対応するため、空チェックを行うように変更（news_nlp, pipeline）。
- ロギングと失敗時のフェイルセーフ動作を明確化
  - OpenAI 呼び出し失敗時は例外を投げずにフェイルセーフ値（0.0）に戻す設計を多くの箇所で採用（news_nlp._score_chunk, regime_detector._score_macro 等）。
  - API の 5xx / ネットワーク障害はリトライ対象、それ以外は即スキップしてログ出力。

Fixed
- .env パースの堅牢化
  - クォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの扱いを改善して .env の読み込みが誤動作しないように修正（config._parse_env_line）。
- market_calendar が不完全（NULL 値等）な場合の挙動を明確化
  - NULL が混入した場合でも曜日ベースのフォールバックを行い一貫した next/prev/get_trading_days の結果を返すように改善（calendar_management）。

Security
- 環境変数の上書き保護
  - 自動ロード時に起動時の os.environ キーセットを protected として保存し、.env / .env.local による既存 OS 環境変数の上書きを防止。

Notes / Implementation details
- ルックアヘッドバイアス防止
  - 多くの関数（score_news, score_regime, factor/research 関数等）は内部で date.today()/datetime.today() を参照せず、明示的な target_date 引数を使用して過去データのみを参照する設計。
- テスト容易性
  - OpenAI 呼び出し用の内部関数（各モジュールの _call_openai_api）や api_key 引数を通じて unittest.mock.patch やテスト用クライアント注入で差し替え可能。
- OpenAI JSON Mode
  - gpt-4o-mini の JSON レスポンスフォーマットを前提に厳密な JSON を期待するが、前後余計テキストが混ざる場合の復元処理も実装。

Breaking Changes
- 本リリースは初期公開版のため後方互換性の議論点は特になし。ただし今後:
  - Settings の env / log_level の許容値検証が厳格なため、環境変数の値が不正な場合は ValueError が投げられます。既存運用でカスタム値を使っている場合は注意してください。
  - score_news / score_regime は OpenAI API キーが未設定の場合 ValueError を送出します。環境変数 OPENAI_API_KEY の設定または api_key の明示的注入が必要です。

今後の予定（非包含）
- strategy / execution / monitoring モジュールの実装拡張（発注ロジック、ストラテジ管理、監視通知等）。
- テストカバレッジの強化（API モック、DuckDB の統合テスト）。
- 性能最適化（大規模データに対する ETL / クエリの改善、バッチパラメータチューニング）。

ご不明点や追記希望の変更点があればお知らせください。
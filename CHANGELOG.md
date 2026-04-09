Changelog
=========
すべての注目すべき変更点を記録します。これは Keep a Changelog の形式に準拠しています。

フォーマット:
- 既存の項目はカテゴリ別（Added / Changed / Fixed / Deprecated / Removed / Security）で記載しています。
- 日付は / バージョンはソース内の __version__ に基づいています。

[Unreleased]
-------------

[0.1.0] - 2026-04-09
--------------------
Added
- パッケージ初回公開: kabusys 0.1.0
  - 高レベル概要: 日本株自動売買システム向けのデータ取得、特徴量計算、AI ニュース解析、
    市場レジーム判定、マーケットカレンダー管理、ETL パイプライン等の基盤機能を実装。

- パッケージメタ情報
  - src/kabusys/__init__.py にて __version__ = "0.1.0"、パッケージの公開 API を定義。

- 環境設定 / .env 読み込み
  - src/kabusys/config.py
    - .env ファイル自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応（テスト向け）。
    - .env パースの堅牢化:
      - export KEY=val 形式対応。
      - シングル/ダブルクォート内でのバックスラッシュエスケープ処理。
      - コメント判定ルール（非クォート文字列内の '#' は直前が空白の場合のみコメントと判定）など。
    - 環境変数取得ユーティリティ（Settings クラス）を提供:
      - J-Quants / kabu ステーション API / LINE / DB パス等のプロパティを定義。
      - バリデーション: PAPER_FILL_MODE（instant|partial|never|reject）、KABUSYS_ENV（development|paper_trading|live）、LOG_LEVEL（DEBUG/INFO/...）など。未設定時は明示的なエラーを発生させるプロパティ（必須キー用 _require）。

- AI ニュース解析 / 市場レジーム判定
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）へ JSON Mode でバッチ問い合わせして銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む。
    - 時間ウィンドウ（JST基準）計算: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime で扱う）。
    - 1銘柄あたりのトークン肥大化対策: 最大記事数 (_MAX_ARTICLES_PER_STOCK=10)、最大文字数 (_MAX_CHARS_PER_STOCK=3000)。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄で分割して API 呼び出し。
    - 再試行ロジック: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ（_MAX_RETRIES）。
    - レスポンス検証: JSON をパースし "results" リスト・各要素の "code"/"score" を検証。スコアは ±1.0 にクリップ。
    - フェイルセーフ: API 失敗やパース失敗時は対象銘柄をスキップして処理継続。DuckDB executemany に空パラメータを渡さない対応（互換性処理）。
    - テストフック: _call_openai_api をモックで差し替え可能。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - MA200 比率計算は target_date 未満のデータのみを使用してルックアヘッドを防止。データ不足時は中立（1.0）として扱う。
    - マクロニュース抽出は news_nlp.calc_news_window で算出されるウィンドウに基づき、マクロキーワードでフィルタしたタイトルを最大 _MAX_MACRO_ARTICLES 件取得。
    - OpenAI 呼び出しは gpt-4o-mini を使用、JSON モードでマクロセンチメント（-1.0〜1.0）を取得。API エラーやパースエラー時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - 再試行・バックオフ、非5xx は即失敗扱いなど堅牢化。最終的なレジームスコアは 0.7*(ma200_dev*scale) + 0.3*macro_sentiment で合成し閾値でラベル付け。
    - DB 書き込みは冪等（BEGIN / DELETE(date) / INSERT / COMMIT）。例外時は ROLLBACK を試みる。

  - 共通設計方針（両モジュール）
    - 外部時間（datetime.today()/date.today()）を直接参照しない設計でルックアヘッドバイアスを防止。
    - OpenAI 呼び出しの内部実装はモジュール間で共有せず、テスト時に差し替えられるように分離。

- 研究用 / ファクター計算
  - src/kabusys/research/
    - factor_research.calc_momentum: 1M/3M/6M リターン、200日MA乖離（ma200_dev）を計算。データ不足時は None を返す。
    - factor_research.calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率等を計算。必要行数未満は None。
    - factor_research.calc_value: raw_financials から直近財務を取得し PER（EPS 0/NULL の場合は None）/ROE を計算。
    - research.feature_exploration.calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一括取得。horizons の検証（1〜252）。
    - research.feature_exploration.calc_ic: ファクター値と将来リターンのスピアマン順位相関（IC）を計算。サンプル数不足時は None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を算出。
    - zscore_normalize を data.stats から再エクスポート（research パッケージの一部として利用可能）。

  - 設計方針:
    - DuckDB 接続を受け取り SQL と純 Python を組み合わせて実装。外部ライブラリ（pandas 等）に依存しない。
    - 本番発注 API へは一切アクセスしない（解析・研究用ロジック）。

- データ管理 / カレンダー / ETL
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダーの管理（market_calendar テーブルに保存）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を提供。
    - DB にデータがない場合は曜日ベースでフォールバック（土日を非営業日扱い）。
    - next/prev_trading_day は最大探索日数 _MAX_SEARCH_DAYS を設定して無限ループ防止。
    - calendar_update_job: J-Quants から差分取得して市場カレンダーを更新（バックフィル _BACKFILL_DAYS、健全性チェック _SANITY_MAX_FUTURE_DAYS）。J-Quants クライアントを利用（jquants_client.fetch_market_calendar / save_market_calendar）。

  - src/kabusys/data/pipeline.py / etl.py
    - ETLResult データクラス: ETL 実行結果を構造化して返す（取得/保存件数、品質問題、エラー等）。
    - ETL パイプライン設計に関するユーティリティ（差分更新、バックフィル、品質チェックの概念等）を実装（jquants_client / quality モジュールを利用する想定）。
    - デフォルトのバックフィル日数やカレンダー先読み日数などの定数を設定し、ETL の挙動を調整可能。
    - ETL 実行の結果は to_dict() でシリアライズ可能（品質問題は小さな dict のリストに変換）。

- 一般実装上の注意点 / 品質
  - DuckDB を主要なローカル DB として利用する設計（DuckDB 接続型注入）。
  - SQL はルックアヘッドを避けるため date < target_date 等の排他条件を適用。
  - DB 書き込みは可能な限り冪等性を保つ（DELETE → INSERT パターンなど）。
  - 各所でログ（logger）による詳細な情報出力と警告出力を行う。
  - 外部 API 呼び出しに対するフェイルセーフ設計（失敗時に 0 や中立値へフォールバックし、処理は継続）。

Deprecated
- なし（初回リリース）

Removed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から取得する。未設定時は ValueError を送出して明示的に失敗させる設計（鍵の漏洩防止や誤動作の早期検出）。

注記（開発者向け）
- テスト容易性のため、AI 呼び出しの内部関数（各モジュールの _call_openai_api）を unittest.mock.patch で差し替え可能。
- DuckDB executemany に空リストを渡せないバージョン互換性のため、空チェックを入れている箇所がある（score_news, etc.）。
- 時刻/日付の扱いは UTC naive datetime と JST の明示的変換を行い、ルックアヘッドのリスクを排除する設計方針。

今後の予定（想定）
- ETL 実行本体（差分計算→jquants_client 呼び出し→quality チェック→ETLResult 返却）や jquants_client の具体実装、monitoring / execution（注文執行）周りの実装強化が期待される箇所。

--- 
（この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノート作成時はリリース日時・著者・マイナーな修正点等を確認のうえ更新してください。）
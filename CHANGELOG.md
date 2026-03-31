# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このプロジェクトはセマンティックバージョニングに従います。

なお、以下の内容はリポジトリ内のコードから推測して作成した変更点・機能説明です。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-31

### Added
- パッケージ初期リリース。kabusys の基本モジュール群を実装。
  - パッケージ識別子:
    - src/kabusys/__init__.py によりバージョン "0.1.0" を公開。公開サブパッケージは data, strategy, execution, monitoring。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない実装）。
  - .env パースの堅牢化:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート内のエスケープ処理、インラインコメントの扱いに対応。
    - クォートなしの行でのコメント判定は '#' の直前が空白またはタブの場合にのみコメントと認識。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供。以下の主要設定プロパティを持つ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等のパス管理（Path オブジェクトで返却）
    - CPU/MEM/ディスク閾値の取得（数値）
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL の検証ロジック、is_live/is_paper/is_dev ヘルパー

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を元に、銘柄ごとにニュースを集約し OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルに書き込む。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime に変換）。
    - バッチ処理: 最大 20 銘柄/チャンク、銘柄ごとに最大 10 記事かつ 3000 文字にトリムして送信。
    - 再試行・フォールバック:
      - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ（最大回数定義あり）。
      - API 失敗時は当該チャンクをスキップして継続（フェイルセーフ）。
    - レスポンスの厳密バリデーションと復元処理（JSON mode の前後ノイズを許容して{}を抽出）。
    - スコアは ±1.0 にクリップ、成功した銘柄のみ部分的に DELETE → INSERT（冪等性および部分失敗時の保護）。
    - テスト容易性: _call_openai_api を patch 可能にしてモックしやすく設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）の直近 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次で 'bull'/'neutral'/'bear' を判定。
    - 重み付け: MA 70%、マクロ 30%。MA は latest_close / MA200 の比率にスケールをかけて合成。
    - マクロニュースは news_nlp の calc_news_window を利用して抽出、OpenAI（gpt-4o-mini, JSON mode）で -1.0〜1.0 の macro_sentiment を取得。
    - API エラー時は macro_sentiment = 0.0 で継続するフェイルセーフ設計。
    - レジーム結果は market_regime テーブルへ冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）で書き込み。
    - ルックアヘッドバイアス対策: datetime.today() / date.today() をスコア計算で直接参照せず、target_date 引数に従う。

- 研究（Research）モジュール（src/kabusys/research）
  - factor_research.py:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER、ROE）などのファクター計算を実装。
    - DuckDB の SQL ウィンドウ関数を活用し prices_daily / raw_financials のみ参照、結果は (date, code) キーの dict リストで返却。
    - データ不足時の None 処理やログ出力を適切に実装。
  - feature_exploration.py:
    - 将来リターン計算（任意の horizon、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク付けユーティリティ、統計サマリーを実装。
    - 外部依存を使わず標準ライブラリ + DuckDB のみで実装。horizons のバリデーションあり。

- データ基盤（src/kabusys/data）
  - calendar_management.py:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティを提供。
    - DB 登録がない場合は曜日ベースのフォールバック（週末除外）。DB 登録がある場合は DB 優先かつ未登録日はフォールバックで補完し一貫性を維持。
    - 夜間バッチ calendar_update_job により J-Quants API から差分を取得して保存（バックフィル、健全性チェックあり）。
  - pipeline.py:
    - ETL パイプラインの骨格と ETLResult（dataclass）を実装。
    - 差分更新、保存（jquants_client の save_* を使用した冪等保存）、品質チェック（quality モジュールとの連携）設計方針を記載。
    - ETLResult は品質問題の要約化、エラー判定プロパティ（has_errors, has_quality_errors）を提供。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティ等を提供。
  - etl.py:
    - ETLResult を公開再エクスポート。

- モジュール公開インターフェースの整理:
  - src/kabusys/ai/__init__.py で score_news を公開。
  - src/kabusys/research/__init__.py で主要研究関数群（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を公開。
  - src/kabusys/data/__init__.py を用意（将来の公開点検向け）。

### Design / Implementation notes（設計上の重要事項）
- ルックアヘッドバイアス対策:
  - AI スコアリング・レジーム判定・ファクター計算はいずれも内部で date.today() を直接参照せず、必ず target_date を引数として受ける設計。
- フェイルセーフ & 冗長性:
  - OpenAI API 呼び出し等はエラー時にフォールバック（例: macro_sentiment = 0.0）することで異常時でも処理を続行する。
  - レスポンスパース失敗や想定外フォーマットにはログを残してスキップする方針。
- テストしやすさ:
  - _call_openai_api 等の内部 API 呼び出しはパッチ可能に設計しユニットテストでモック可能。
- DuckDB 互換性への配慮:
  - executemany に空リストを渡さないチェック、list 型バインドの互換性回避（個別 DELETE の使用）など、DuckDB の挙動に合わせた実装。
- ロギング・監査:
  - 各処理は詳細なログ（info/debug/warning/exception）を出力するよう実装。

### Known limitations / 未実装事項（コードから推測）
- Strategy（売買戦略）、Execution（発注）および Monitoring モジュールの中身は公開サブパッケージとして存在するが、この差分では主要実装は示されていない（将来的な追加想定）。
- 一部外部クライアント（jquants_client, quality, jquants_client の fetch/save 実装等）は別モジュールに依存しているため、外部 API 連携ロジックはそれらの実装に依存する。
- PBR・配当利回りなどのバリューファクターの拡張は未実装（コメントとして言及あり）。

### Security
- 特にセキュリティフィックスはなし。ただし API キーの取り扱いは環境変数に依存し、環境設定ファイルの自動読み込みに対して無効化フラグを用意している。

---

作者注: 上記はリポジトリ内のソースコードから推測して作成した CHANGELOG です。実際のリリースノートに含める文言や日付はプロジェクトのリリースポリシーに従って必要に応じて調整してください。
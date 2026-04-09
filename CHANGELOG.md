# CHANGELOG

すべての変更はKeep a Changelogの形式に準拠して記載しています。セマンティックバージョニングを採用します。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-09
初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加しました。主な機能は以下の通りです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名とバージョン（0.1.0）、公開サブパッケージ一覧を定義。

- 環境変数・設定管理
  - src/kabusys/config.py:
    - .env / .env.local 自動ロード機構を実装（プロジェクトルートを .git / pyproject.toml から検出）。
    - .env パーサを独自実装（export 形式対応、クォート内エスケープ、インラインコメントの扱いなど）。
    - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）対応。
    - 環境変数取得ユーティリティと必須キーチェック（_require）。
    - 各種設定プロパティを公開する Settings クラス（J-Quants / kabuステーション / LINE / DBパス / Paper Trading / 監視閾値 / ログレベル / 環境種別等）。
    - 設定値のバリデーション（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）。

- AI関連（ニュースNLP・市場レジーム判定）
  - src/kabusys/ai/news_nlp.py:
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC に変換）calc_news_window 実装。
    - バッチ処理（最大20銘柄／チャンク）、記事トリム（最大記事数・最大文字数）、レスポンス検証、スコアクリッピング、リトライ（429/ネットワーク/タイムアウト/5xx）などを実装。
    - DuckDB 互換性対策（executemany の空リスト回避など）。
    - API呼び出し部はテスト向けに差し替え可能（_call_openai_api）。

  - src/kabusys/ai/regime_detector.py:
    - ETF 1321 の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算、マクロキーワードでのタイトル抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API失敗時フェイルセーフ（macro_sentiment=0.0）・指数バックオフリトライ・レスポンスパース例外処理などを実装。
    - テスト時に差し替え可能な内部 API 呼び出し実装（_call_openai_api）。

- Data（ETL / カレンダー管理 / パイプライン）
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理ユーティリティ（market_calendar テーブル）を実装。
    - 営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。DB 登録値優先だが未登録日は曜日ベースでフォールバック。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants からの差分取得、バックフィル、健全性チェック、保存処理）。
    - 最大探索日数制限や各種定数を導入して無限ループや異常データを防止。

  - src/kabusys/data/pipeline.py:
    - ETL 処理の設計に基づくパイプライン基盤（差分取得、保存、品質チェックの連携）を実装。
    - ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラー等の集約）。
    - デフォルトの backfill 日数やカレンダー先読み等の定数を定義。

  - src/kabusys/data/etl.py:
    - pipeline.ETLResult を再エクスポートして公開インターフェースを簡素化。

  - src/kabusys/data/__init__.py:
    - data パッケージの準備（モジュール分割）。

- Research（ファクター計算・探索）
  - src/kabusys/research/factor_research.py:
    - モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB を用いた SQL と Python の組合せで、prices_daily / raw_financials テーブルからファクターを算出。
    - データ不足時の扱い（None の返却）、ログ出力、スキャン範囲のバッファ等を実装。

  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等非依存で標準ライブラリ + DuckDB で動作する実装。
    - rank は同順位を平均ランクにする実装と浮動小数丸め対策を含む。

  - src/kabusys/research/__init__.py:
    - 主要な関数を公開（calc_momentum 等と zscore_normalize の re-export）。

- その他
  - src/kabusys/ai/__init__.py: score_news を公開。
  - ロギング出力・デバッグ情報を各モジュールで適切に追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から解決し、未設定時は ValueError を投げる設計で鍵漏洩の直接的なリスクを低減。
- 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

### Notes / 設計上の重要点
- ルックアヘッドバイアス防止: AI/研究関連処理は datetime.today()/date.today() に依存しない（target_date を入力に取り、DB クエリは target_date 未満／排他等の注意を払っている）。
- DB 書き込みは可能な限り冪等性を保つ（DELETE→INSERT、ON CONFLICT、BEGIN/COMMIT/ROLLBACK の扱い）。
- DuckDB のバージョン差分（executemany の空リスト等）に対する互換性考慮が施されている。
- OpenAI 呼び出しはリトライとバックオフ、レスポンスバリデーションにより堅牢化している。テスト時には内部のAPI呼び出し関数をモック可能。

今後の予定（例）
- strategy / execution / monitoring の具体実装追加
- 単体テスト・統合テストの追加
- ドキュメント（APIリファレンス、運用手順）の整備

---

参考: リリース日にはリポジトリの初回公開日・タグ付けを行ってください。
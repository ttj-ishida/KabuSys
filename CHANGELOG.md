# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このファイルは Keep a Changelog の様式に準拠します。  

- リリースノートは安定性・再現性のために可能な限り具体的に記載しています。
- 日付はコードベースから推測して設定しています（必要に応じて修正してください）。

## [Unreleased]
- （今後の変更をここに記載）

## [0.1.0] - 2026-04-03

初期リリース。日本株自動売買（KabuSys）パッケージの基盤的機能を実装しました。  
主要な追加点、設計上の方針、安全性や堅牢化のための実装についてまとめます。

### Added
- 基本パッケージ構成
  - kabusys パッケージの公開 API（data, strategy, execution, monitoring）を定義。
  - バージョン定義: `__version__ = "0.1.0"`。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: __file__ を起点に `.git` または `pyproject.toml` を探索して自動ロード対象ルートを決定。
  - 自動ロードの無効化環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - .env のパース強化:
    - `export KEY=val` 形式やシングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - コメントの扱い（クォート内無視、非クォートでの '#' の扱いなど）を考慮。
  - 環境変数保護機能（既存 OS 環境変数の上書きを防ぐ protected set）。
  - 設定アクセス用 `Settings` クラスを提供（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定）。
    - デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）を提供。
    - 必須キー未設定時は `ValueError` を送出する `_require` を実装。
    - 環境値の妥当性検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI 関連: ニュース NLP と市場レジーム判定（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を行う `calc_news_window` を実装。
    - バッチ処理、チャンクサイズ制限（最大 20 銘柄 / チャンク）、1銘柄あたり記事数・文字数制限を実装。
    - OpenAI 呼び出しのリトライ（429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ）。
    - レスポンス検証（JSON 抽出、results キー、コード整合性、数値チェック）と ±1.0 でのクリッピング。
    - 部分失敗時に既存スコアを消さないよう、書き込みは対象コード絞り込み（DELETE → INSERT）で冪等に実施。
    - テスト容易性のため、OpenAI 呼び出し箇所は差し替え可能（patch 用に `_call_openai_api` を定義）。
  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
    - prices_daily と raw_news を参照して MA 比率計算・マクロ記事抽出を実施。
    - OpenAI でマクロセンチメントを取得（JSON レスポンスを期待）し、API エラー時は macro_sentiment=0.0 でフェイルセーフ継続。
    - 計算結果は `market_regime` テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。失敗時は ROLLBACK を試みる。

- データ基盤（kabusys.data）
  - calendar_management モジュール（JPX カレンダー管理）
    - market_calendar を利用した営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - DB 登録優先、未登録日は曜日ベースでのフォールバック（週末を休日とみなす）。
    - 夜間の calendar_update_job 実装（J-Quants から差分取得、バックフィル、健全性チェック、保存）。
  - pipeline / ETL（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスをエクスポート（取得件数・保存件数・品質問題・エラー情報を収集）。
    - 差分更新・バックフィル・品質チェックの方針を実装（jquants_client 経由での保存・品質問題を集約して返す設計）。

- 研究用モジュール（kabusys.research）
  - factor_research
    - momentum / volatility / value ファクター計算を実装（prices_daily / raw_financials を参照）。
    - 各関数は (date, code) ベースの dict リストを返す。
    - ATR / MA200 / 各モメンタム（1M/3M/6M）・出来高・平均売買代金などを算出。
  - feature_exploration
    - 将来リターン計算（任意ホライズン）、IC（Spearman）計算、rank（同順位は平均ランク）、factor_summary（基本統計）を実装。
    - pandas 等へ依存せず標準ライブラリのみで実装。

### Changed
- （初期リリースのため該当なし）

### Fixed / Robustness / Safety
- .env 読み込み時の I/O エラーに対して警告を出し安全にスキップ。
- OpenAI 呼び出しのリトライロジックを実装し、RateLimit / Connection / Timeout / 5xx に対処。最終的に失敗した場合は警告を記録してフェイルセーフ挙動（スコア = 0.0 等）で継続。
- 外部 API レスポンスのパース失敗時は例外を投げず空スコア（skip）とすることで部分障害に強い設計。
- DB 書き込みは冪等化（DELETE→INSERT）し、部分失敗で他データを消さない設計。
- DuckDB のバージョン依存性を考慮した executemany 空リスト回避や list バインドの回避など互換性対策を実施。
- 時間に関する実装（score_news / score_regime 等）は datetime.today() / date.today() を内部で直接参照せず、外部から target_date を取ることでルックアヘッドバイアスを防止。

### Security & Configuration notes
- 以下の環境変数が利用される（必須・任意あり）:
  - 必須（アクセス時に未設定なら ValueError）: OPENAI_API_KEY（AI 関連関数で必要）、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD
  - 任意/デフォルトあり: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH、KILL_FLAG_CLEAR_ON_START、CPU/MEMORY/DISK 閾値 等
  - 自動 .env ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- .env 自動ロードでは OS 環境変数を protected として上書きされないよう保護。

### Notes / Limitations
- OpenAI モデル: デフォルトで gpt-4o-mini を使用。API のスキーマや SDK の違いに備えてエラーハンドリングを柔軟に実装。
- news_nlp と regime_detector はテスト容易性のため内部の OpenAI 呼び出しを差し替え可能。
- 一部集計・解析は DuckDB 上の SQL と Python ロジックの組合せで実装しており、本番用 DB と同等のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を前提とする。
- 初期実装では PBR や配当利回り等の一部バリューファクターは未実装。

### Breaking Changes
- なし（初期リリース）

---

もし特定の変更点に関して日付や詳細（例: リリース日を別にしたい、特定のチケット番号やコミットハッシュを追加したい）があれば教えてください。必要に応じて追記・修正します。
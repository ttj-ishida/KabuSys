# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。
このプロジェクトの初回リリースを記録しています。

全般的な注意:
- 本リリースはバージョン 0.1.0（初期実装）です。
- 実装方針として「ルックアヘッドバイアスを避ける」「DB 書き込みは冪等化」「外部 API 呼び出しは堅牢なリトライ／フォールバックを行う」が貫かれています。

## [Unreleased]

（現時点なし）

## [0.1.0] - 2026-03-31

Added
- パッケージ基盤
  - パッケージルート: `kabusys` 初期モジュールとしての公開（__version__ = "0.1.0"）。
  - __all__ に `data`, `strategy`, `execution`, `monitoring` を想定した公開構成を設定。

- 設定 / 環境変数管理 (`kabusys.config`)
  - プロジェクトルート自動検出: .git または pyproject.toml を基準にプロジェクトルートを探索する機能を実装。これによりカレントワーキングディレクトリに依存せず .env を参照可能。
  - .env ファイル自動読み込み: 優先順位は OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサー強化:
    - `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントへの対応。
    - クォートなし値の '#' をコメント判定する際の細かな挙動調整。
  - 環境値取得ユーティリティ `Settings` クラスを提供:
    - J-Quants、kabuステーション、Slack、データベースパス（DuckDB/SQLite）、監視用閾値、実行環境（development/paper_trading/live）等のプロパティ。
    - 必須変数未設定時は明確なエラーメッセージで ValueError を送出。
    - `env` と `log_level` の値検証を実装（有効値チェック）。
    - `is_live`, `is_paper`, `is_dev` の便宜プロパティを提供。

- AI モジュール（ニュース NLP / レジーム判定）
  - `kabusys.ai.news_nlp`:
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して `ai_scores` テーブルへ書き込む処理を実装。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST、内部は UTC naive）を提供 (`calc_news_window`)。
    - バッチ処理（最大 20 銘柄／バッチ）、1 銘柄あたりの記事数・文字数上限（トリム）を実装してトークン肥大化を制御。
    - レート制限・ネットワーク断・タイムアウト・5xx サーバーエラーに対するエクスポネンシャルバックオフとリトライ処理を実装。
    - OpenAI の JSON Mode 出力のバリデーション（JSON 抽出、results リスト検証、コード・スコアの型検査）を実装。未知コードは無視、スコアは ±1.0 にクリップ。
    - 部分的な失敗に備え、スコアの書き込みは対象コードのみ DELETE → INSERT で行い既存データの保護を行う（冪等性）。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に設計（モジュール内で独立）。
  - `kabusys.ai.regime_detector`:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定する機能を実装。
    - ma200_ratio の計算は target_date 未満のみを参照してルックアヘッドを防止。
    - マクロニュースはニュース NLP のウィンドウ計算を利用してフィルタしたタイトルを抽出。
    - OpenAI 呼び出しは gpt-4o-mini を用い、API エラー時はマクロセンチメントを 0.0 にフォールバック（フェイルセーフ）。
    - レジームの計算と判定閾値を定義し、結果を `market_regime` テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データプラットフォーム関連 (`kabusys.data`)
  - カレンダー管理 (`calendar_management`):
    - JPX カレンダーの夜間バッチ更新ジョブ（J-Quants API 経由で差分取得して market_calendar に保存）を実装。
    - 営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を提供。DB 登録値を優先し、未登録日は曜日ベースでフォールバック。
    - 安全対策（探索上限、バックフィル、健全性チェック）を実装。
  - ETL パイプライン (`pipeline`):
    - ETL の実行結果を表す `ETLResult` dataclass を提供（取得件数、保存件数、品質チェック結果、エラー一覧など）。
    - 差分取得・バックフィル・品質チェック等の設計方針を反映した土台実装（jquants_client / quality モジュールとの連携を想定）。
  - ETL の公共インターフェースとして `data.etl` で `ETLResult` を再エクスポート。

- リサーチ機能 (`kabusys.research`)
  - ファクター計算 (`factor_research`):
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、出来高・売買代金指標）、Value（PER、ROE）など主要ファクターを DuckDB SQL ベースで実装。
    - データ不足時の扱い（None）や営業日スキャン幅のバッファ等を考慮。
  - 特徴量探索 (`feature_exploration`):
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（スピアマンのランク相関）計算、ランク付けユーティリティ、ファクターの統計サマリーを実装。
    - Pandas など外部依存無しで実装（標準ライブラリ + DuckDB）。
  - `research.__init__` で主要関数をエクスポート（zscore 正規化は data.stats から参照）。

- テスト・拡張性の配慮
  - OpenAI 呼び出しの抽象化（モジュール内関数を置き換え可能）や環境ロードを無効化するフラグ等、ユニットテストを容易にする設計が施されています。
  - DuckDB を前提とした SQL 実装により高速なローカル分析が可能。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- API キー等の必須値は Settings 経由で取得し、未設定時は明示的にエラーにすることで誤った公開を防ぐ設計。

Notes / 補足
- OpenAI（gpt-4o-mini）や J-Quants クライアント、DuckDB など外部依存が必要です。実行環境では適切な環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を設定してください。
- 一部ファイル（例: pipeline の終端など）が実装中である可能性があります。将来的な修正で小さな API 変更や実装補完が入る場合があります。

[0.1.0]: v0.1.0 - 2026-03-31
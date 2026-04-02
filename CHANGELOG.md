# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このドキュメントは提供されたコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-02
初回公開リリース。本リリースはデータインジェスト、データ処理（リサーチ）、機械学習補助（LLMを用いたニュース解析）、および環境設定周りの基盤機能を実装します。

### Added
- パッケージ基礎
  - `kabusys` パッケージの初期公開。バージョンは `0.1.0`。
  - パッケージ公開インターフェース: `data`, `strategy`, `execution`, `monitoring`（__all__ 項目）。
- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイル読み込みの自動化（プロジェクトルート判定: `.git` または `pyproject.toml` を基準）。
  - .env パーサーの実装（コメント行、`export KEY=...`、シングル/ダブルクォートおよびエスケープ対応、インラインコメントの扱い）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
  - 環境変数取得ユーティリティ `Settings` クラスを追加（`settings` インスタンスを公開）。
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム環境（KABUSYS_ENV, LOG_LEVEL）等のプロパティを提供。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値チェック）。
    - ファイルパスは `Path` として返却（展開済み）。
- AI（LLM）連携モジュール (`kabusys.ai`)
  - ニュースセンチメント解析 `score_news`（`news_nlp.py`）
    - raw_news と news_symbols を使い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini、JSON mode）へバッチ送信。
    - バッチサイズ、文字数・記事数上限、JSON レスポンスのバリデーション実装。
    - エラー（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフリトライ、失敗時はスキップ（フェイルセーフ）。
    - スコアは ±1.0 にクリップし、成功した銘柄のみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
    - `calc_news_window` による JST ベースのニュース収集ウィンドウ計算（ルックアヘッド対策）。
    - テスト用に OpenAI 呼び出し関数を差し替え可能な設計（モック可能）。
  - 市場レジーム判定 `score_regime`（`regime_detector.py`）
    - ETF (1321) の 200 日移動平均乖離（重み 70%）と LLM によるマクロセンチメント（重み 30%）を合成し、日次でレジームを判定（'bull' / 'neutral' / 'bear'）。
    - DuckDB からのデータ参照はルックアヘッドを防ぐ条件（date < target_date 等）で実装。
    - LLM 呼び出しは JSON mode を利用、リトライとフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - 計算結果は `market_regime` テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI クライアント呼び出しは別実装のヘルパー関数で分離（モジュール結合の抑制）。
- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算 (`factor_research.py`)
    - モメンタム：1M/3M/6M リターン、200日 MA 乖離（`calc_momentum`）。
    - ボラティリティ／流動性：20日 ATR、相対ATR、平均売買代金、出来高比率（`calc_volatility`）。
    - バリュー：PER / ROE（raw_financials と prices_daily 組合せ）（`calc_value`）。
    - DuckDB を用いた SQL + Python 実装、外部 API へはアクセスしない設計。
    - 不足データ時は None を返す等の堅牢な動作。
  - 特徴量探索 (`feature_exploration.py`)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）（`calc_forward_returns`）。
    - IC（Spearman ランク相関）計算（`calc_ic`）。
    - 値をランクへ変換する `rank`（同順位は平均ランク）。
    - ファクター統計サマリー `factor_summary`（count/mean/std/min/max/median）。
    - pandas 等に依存しない純標準ライブラリ実装。
- データプラットフォーム / ETL (`kabusys.data`)
  - カレンダー管理 (`calendar_management.py`)
    - JPX カレンダーの取得・保存ロジックおよび営業日判定ユーティリティ群:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar が未取得の場合の曜日ベースフォールバック。DB 登録値を優先する一貫性を保持。
    - 夜間バッチ更新ジョブ `calendar_update_job`：J-Quants から差分取得、バックフィル、健全性チェック、冪等保存を実装。
  - ETL パイプライン (`pipeline.py`, `etl.py`)
    - ETL の結果を表現する `ETLResult` dataclass を公開（`kabusys.data.ETLResult` を再エクスポート）。
    - 差分更新、IDempotent 保存、品質チェック統合の設計に基づくパイプライン骨格を実装。
    - DuckDB を前提としたヘルパー（テーブル存在チェック、MAX 日付取得など）。
    - quality モジュールとの連携を想定した品質問題収集機構を備える。
- その他
  - DuckDB を主要なローカルデータストアとして利用（各モジュールが DuckDB 接続を引数に受ける）。
  - OpenAI SDK（Chat Completions）を JSON mode で利用する設計。モデルはデフォルトで "gpt-4o-mini"。
  - ロギングを各所で適切に出力（info/warning/debug/exception）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能（テスト容易化）かつ環境変数 `OPENAI_API_KEY` をデフォルト参照。未設定時は明示的に ValueError を投げるためキー漏洩などの静的検出を容易にする設計。

### Notes / 実装上の重要な設計判断（ドキュメント的注釈）
- ルックアヘッドバイアス防止:
  - すべての時刻ベース処理は内部で `date.today()` / `datetime.today()` を直接参照しないか、外部から `target_date` を注入する設計。
  - DB クエリには常に対象日より前のデータのみを使用する条件が組み込まれている。
- フェイルセーフ:
  - LLM/API 呼び出し失敗時は基本的に例外を投げずに安全側のデフォルト（例: macro_sentiment=0.0、スコア未取得→スキップ）で継続する方針。
- テスト可能性:
  - OpenAI 呼び出し部分はモックやパッチで差し替え可能なように `_call_openai_api` 等のラッパー関数を用意。
- DB 書き込み:
  - 各種書き込みは冪等性を重視（DELETE → INSERT や ON CONFLICT 相当）およびトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
- 互換性:
  - DuckDB バージョン差異（executemany の空リスト不可等）への配慮が組み込まれている。

---

この CHANGELOG はコードベースからの推測に基づいて作成しています。実際のリリースノートには、テスト実績、既知の制限、将来の変更計画などを追記することを推奨します。必要であれば各機能ごとにより詳細な変更点（関数シグネチャ、戻り値、例外仕様、ログ出力例など）を追加します。
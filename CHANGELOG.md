# Changelog

すべての変更点は Keep a Changelog の形式に従って記載しています。  

タグ付け規則: バージョンはパッケージ内部の `__version__`（現在 0.1.0）に準拠しています。

また、本リリースノートはソースコードの内容から推測して作成しています（実行ログ・外部ドキュメントは参照していません）。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: `kabusys.__init__`（__version__ = 0.1.0）。
  - モジュール公開: `data`, `strategy`, `execution`, `monitoring` を __all__ で公開。

- 設定・環境管理 (`src/kabusys/config.py`)
  - .env ファイルおよび環境変数の読み込み機能を実装。
    - プロジェクトルートを `.git` または `pyproject.toml` を基準に探索して自動的に .env を読み込む（配布後の動作を考慮）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env のパース機能（コメント、exportプレフィックス、クォート内のエスケープ等に対応）。
  - 環境設定ラッパー `Settings` を提供（プロパティ経由で必須/任意設定を取得）。
    - 必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - OpenAI 連携は `OPENAI_API_KEY`（API 呼び出し時に参照される）
    - DB 路: デフォルト `DUCKDB_PATH=data/kabusys.duckdb`, `SQLITE_PATH=data/monitoring.db`
    - 監視関連デフォルト: `PID_FILE_PATH=data/execution.pid`、CPU/MEM/DISK の閾値プロパティ
    - 環境種別検証（development / paper_trading / live）およびログレベル検証

- AI（自然言語処理）機能 (`src/kabusys/ai`)
  - ニュースNLP スコアリング (`news_nlp.py`)
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）にバッチで投げてセンチメントを算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事選定。
    - バッチサイズ、記事/文字数制限、JSON Mode 応答のバリデーション、スコア ±1.0 クリップ。
    - レート制限・ネットワーク断・5xx に対する再試行（指数バックオフ）。
    - レスポンスパース失敗やAPIエラーは個別にフォールバック（例外を上位に投げずスキップ）する設計。
    - テスト容易性のため OpenAI 呼び出しを内部関数で切り替え可能に設計（ユニットテストで patch して差替え可）。
  - 市場レジーム判定 (`regime_detector.py`)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を算出。
    - ニュースは `news_nlp.calc_news_window` を使用してウィンドウを決定し、マクロキーワードでフィルタしたタイトル群を LLM に投げて JSON レスポンスで macro_sentiment を取得。
    - LLM 呼び出しは再試行とフォールバック（API 全滅時に macro_sentiment=0.0）を実装。
    - 計算結果は `market_regime` テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。

- データプラットフォーム（Data）機能 (`src/kabusys/data`)
  - カレンダー管理 (`calendar_management.py`)
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job`（J-Quants から差分取得、バックフィル、健全性チェック、保存）。
    - 営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。
    - DB に calendar がない場合は土日ベースでフォールバックする設計。
    - 最大探索日数の制約と日付型の扱いに注意。
  - ETL パイプライン (`pipeline.py`) と ETL 結果型の公開 (`etl.py`)
    - 差分取得・保存・品質チェックのワークフロー設計に対応する ETLResult データクラスを実装。
    - ETLResult は取得数・保存数・品質問題・エラー一覧を持ち、辞書化メソッドを提供（監査ログ向け）。
    - ETL の補助ユーティリティ（テーブル存在確認、最大日付取得等）を実装。
  - 外部 J-Quants クライアント（`jquants_client`）を利用する想定（モジュールから fetch/save を呼び出す設計）。

- リサーチ（研究）機能 (`src/kabusys/research`)
  - ファクター計算 (`factor_research.py`)
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離
    - Volatility / Liquidity: 20 日 ATR、20 日平均売買代金、出来高比率
    - Value: PER（株価 / EPS）, ROE（raw_financials から取得）
    - DuckDB 上の SQL を活用した計算（prices_daily, raw_financials 参照）。データ不足時は None を返す。
  - 特徴量探索 (`feature_exploration.py`)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、rank/summary 関数。
    - pandas 等に依存せず標準ライブラリと DuckDB SQL の組合せで実装。
  - 便利関数の再エクスポート（zscore_normalize 等）。

### 変更 (Changed)
- （初回リリースのため変更履歴なし）

### 修正 (Fixed)
- （初回リリースのため修正履歴なし）

### 削除 (Removed)
- （初回リリースのため削除履歴なし）

### 非推奨 (Deprecated)
- （初回リリースのため非推奨事項なし）

### セキュリティ (Security)
- OpenAI API キーや外部 API トークンは環境変数経由で取得し、直接コードに埋め込まない設計。
- .env 読み込みはデフォルトで有効だが、テストや特殊環境向けに `KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化をサポート。

---

注意事項・実装上の設計ノート（利用者向けの補足）
- LLM（OpenAI）連携
  - news_nlp / regime_detector は gpt-4o-mini を想定。API 呼び出し時は JSON Mode（response_format）を使い、厳密な JSON レスポンスを期待する実装になっている。
  - レスポンスパースや API の失敗はフェイルセーフ（多くはスコア 0.0 あるいはスキップ）で扱うため、API 障害時もシステム全体が停止しにくい設計。
  - テスト時は内部の _call_openai_api をモックすることを想定している。
- ルックアヘッドバイアス対策
  - 日付判定やウィンドウ計算で datetime.today()/date.today() を直接参照しない実装（すべて target_date 引数に依存）。バックテストや再現性に配慮。
- DuckDB の互換性
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）を考慮した空配列チェックを行っている箇所がある。
- 必須環境変数
  - 実行に必須な環境変数が未設定の場合、Settings のプロパティや AI スコア関数は ValueError を発生させる（明示的な失敗を促す設計）。

もしこの CHANGELOG で補足してほしい点（リリース日付の変更、より詳細なファイル/関数列挙、既知の制限事項の記載など）があれば教えてください。
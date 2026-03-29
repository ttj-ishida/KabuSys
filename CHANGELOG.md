# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

最新: 0.1.0 (初回リリース) — 2026-03-29

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買・データプラットフォーム向けの基盤ライブラリを追加しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`。
  - 主要サブパッケージの公開: `data`, `strategy`, `execution`, `monitoring` を __all__ に設定。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイル自動読み込み機能を実装（プロジェクトルートの検出は `.git` または `pyproject.toml` を基準）。
  - .env のパース機能を強化:
    - `export KEY=value` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理を考慮。
    - コメント扱いのルール（クォート無しの場合は '#' の直前に空白があるとコメントとみなす）を実装。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - 環境変数取得ユーティリティ `_require` と `Settings` クラスを提供（必須キーの検証、既定値、パス展開など）。
  - 有効な環境（`development`, `paper_trading`, `live`）とログレベルの検証ロジックを追加。
  - デフォルト DB パス: DuckDB `data/kabusys.duckdb`、SQLite `data/monitoring.db`。

- データ関連 (`kabusys.data`)
  - ETL パイプラインの型定義・結果クラス:
    - `ETLResult` を公開（取得件数・保存件数・品質問題・エラーの集計を含む）。
  - カレンダー管理 (`calendar_management`):
    - JPX マーケットカレンダー管理ロジック（market_calendar テーブルの照会・更新、営業日判定）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - 夜間更新ジョブ `calendar_update_job` を実装（J-Quants から差分取得・バックフィル・健全性チェック）。
    - カレンダーが無い場合の曜日ベースフォールバック設計（DBデータが薄い場合でも一貫性を保つ）。
  - ETL ユーティリティ / パイプライン基盤 (`pipeline`):
    - 差分取得・保存・品質チェックを行う設計（J-Quants クライアント連携を想定）。
    - DuckDB の互換性を考慮したテーブル存在チェックや最大日付取得ロジックを実装。

- 研究・解析ツール (`kabusys.research`)
  - Factor / Feature モジュールを実装・公開:
    - `calc_momentum`, `calc_volatility`, `calc_value`（ファクター計算）。
    - `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`（特徴量探索・統計）。
    - Zスコア正規化は `kabusys.data.stats.zscore_normalize` を参照して再利用可能にしたエクスポート設定。

- ファクター計算 (`research/factor_research.py`)
  - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
  - Volatility / Liquidity: 20日 ATR、相対ATR(atr_pct)、20日平均売買代金、出来高比率を計算。
  - Value: raw_financials と当日の株価から PER, ROE を計算（EPS が無効な場合は None）。
  - DuckDB のウィンドウ関数を活用した効率的な SQL 実装。

- 将来リターン・IC・集計 (`research/feature_exploration.py`)
  - 将来リターン calc_forward_returns（任意ホライズン、最大252営業日制約）。
  - IC（Spearman のランク相関）計算 `calc_ic`（欠損・同値処理を考慮）。
  - ランク関数 `rank`（同順位は平均ランク、丸めによる ties 対応）。
  - `factor_summary` による基本統計量（count, mean, std, min, max, median）計算。

- AI / NLP（ニュース・マクロ評価） (`kabusys.ai`)
  - ニュースNLP スコアリング (`news_nlp.py`):
    - raw_news + news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを取得。
    - JST 基準のタイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの上限記事数・文字数制限、レスポンス検証、スコアの ±1.0 クリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ処理を実装。
    - OpenAI の JSON mode を利用し、レスポンスを慎重にパース・バリデーションする実装。
    - DuckDB 互換性（executemany の空リスト制約）を考慮した DB 書き込みロジック（DELETE → INSERT の置換戦略）。
  - 市場レジーム判定 (`regime_detector.py`):
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を組合せて日次レジームを判定（'bull' / 'neutral' / 'bear'）。
    - マクロニュース取得はニュース NLP のウィンドウ計算を利用。LLM 呼び出しは独立実装でモジュール結合を抑制。
    - OpenAI 呼び出しに対するリトライ／フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実施。
    - 最終結果は DuckDB の market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- API キー・呼び出しの取り扱い
  - OpenAI API キーは関数引数で注入可能。None の場合は環境変数 `OPENAI_API_KEY` を参照。
  - テスト時に差し替え可能なプライベート呼び出しラッパー（_call_openai_api）を配置し、unittest.mock による置換を想定。

### 変更 (Changed)
- 初回リリースのため変更履歴はありません（ベースラインを確立）。

### 修正 (Fixed)
- 初回リリースのため修正履歴はありません。

### 注意点・設計方針（ドキュメント的メモ）
- 全ての時刻関連処理はルックアヘッドバイアス回避のため datetime.today() / date.today() を直接参照しない設計（関数呼び出し側で target_date を注入）。
- AI 呼び出しはフェイルセーフを重視し、API 失敗時も例外を波及させず処理を継続する方針（ただし DB 書き込み時の例外は上位に伝播）。
- DuckDB のバージョン差分・制約（executemany の空リスト等）を考慮した実装。
- .env パースは多くの実運用ケース（クォート、エスケープ、exportプレフィックス、インラインコメント）に対応。

### 既知の未完（今後の TODO / 限定）
- 一部ファイルで実装の続きや追加ユーティリティが想定される（例: pipeline 内のさらなるETLフロー実装、データ保存の詳細など）。ただし現状で主要な API とユーティリティは提供済み。

---

作成・更新に関する要望（翻訳・追記・日付変更など）があればお伝えください。必要に応じてリリースごとの詳細な差分（ファイル単位）も作成します。
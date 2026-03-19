# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このファイルは Keep a Changelog の慣例に従っています。

現在のパッケージバージョン: 0.1.0

## [0.1.0] - 2026-03-19
初回リリース（推測）。以下はコードベースから推測して作成した主な追加機能・実装内容の一覧です。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを定義 (`src/kabusys/__init__.py`)。公開モジュール: `data`, `strategy`, `execution`, `monitoring`。
  - パッケージバージョン `__version__ = "0.1.0"` を設定。

- 環境設定 / 設定管理
  - `.env` / `.env.local` を自動読み込みする設定ローダーを実装（プロジェクトルートの検出: `.git` または `pyproject.toml` を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。 (`src/kabusys/config.py`)
  - `.env` 解析の堅牢化（export 形式対応、シングル/ダブルクォート・エスケープ処理、インラインコメント処理）。  
  - `Settings` クラスを追加し、J-Quants / kabu API / Slack / DB パス / 環境切替などのプロパティを提供。必須値未設定時は明示的に例外を発生させる。環境値の検証（`KABUSYS_ENV`、`LOG_LEVEL`）を実装。

- データ取得・保存（J-Quants API）
  - J-Quants API クライアントを実装（HTTP ユーティリティ、ID トークン取得、ページネーション対応）。主な API 呼び出し関数:
    - `get_id_token`（refresh token から id token 取得）
    - `fetch_daily_quotes`
    - `fetch_financial_statements`
    - `fetch_market_calendar`
  - API 呼び出しに対してレート制限（120 req/min）の固定間隔スロットリングを導入（内部 `_RateLimiter`）。リトライ（指数バックオフ、最大 3 回）と 401 時のトークン自動リフレッシュを実装。 (`src/kabusys/data/jquants_client.py`)
  - DuckDB への保存用関数（冪等性を意識した実装）:
    - `save_daily_quotes`（`raw_prices` へ挿入、ON CONFLICT DO UPDATE）
    - `save_financial_statements`（`raw_financials` へ挿入、ON CONFLICT DO UPDATE）
    - `save_market_calendar`（`market_calendar` へ挿入、ON CONFLICT DO UPDATE）
  - 入出力パース用ユーティリティ `_to_float`, `_to_int` を追加し、不正値を安全に扱う。

- ニュース収集（RSS）機能
  - RSS フィード取得・前処理・DB 保存パイプラインを実装。主要な機能:
    - RSS フェッチ (`fetch_rss`)：gzip 解凍、Content-Length/実読み込み上限（10MB）による保護、XML パース（defusedxml 使用）による安全化。
    - URL 正規化（トラッキングパラメータ除去）と記事 ID の生成（正規化 URL の SHA-256 先頭32文字）。
    - 記事前処理（URL 除去、空白正規化）。
    - `save_raw_news`：チャンク化して `raw_news` に挿入し、実際に挿入された記事 ID を返す（INSERT ... RETURNING を利用）。トランザクション管理（コミット/ロールバック）。
    - `save_news_symbols` / `_save_news_symbols_bulk`：記事と銘柄コードの紐付けを一括で冪等保存。
    - 銘柄コード抽出ユーティリティ `extract_stock_codes`（テキスト中の 4 桁数字を候補に、既知銘柄セットでフィルタ）。
    - 統合ジョブ `run_news_collection`：複数ソースの収集、個別ソースごとのエラーハンドリング、記事挿入・銘柄紐付け。
  - SSRF 対策: リダイレクト時の検証ハンドラ、ホストのプライベートアドレスチェック、許可スキームの制限（http/https のみ）。 (`src/kabusys/data/news_collector.py`)

- Research / Factor 計算
  - 特徴量探索・研究ユーティリティ（外部ライブラリに依存せず標準ライブラリ中心で実装）:
    - `calc_forward_returns`：指定日から複数ホライズン（例: 1,5,21 営業日）の将来リターンを DuckDB の `prices_daily` 参照で計算。
    - `calc_ic`：ファクターと将来リターンのスピアマンランク相関（IC）を計算（ランク付けは同順位を平均ランクとして扱う）。
    - `rank`（同順位の平均ランク処理、丸めによる tie 対応）および `factor_summary`（count/mean/std/min/max/median）を実装。 (`src/kabusys/research/feature_exploration.py`)
  - ファクター計算群（`factor_research`）:
    - `calc_momentum`：mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。過去データ不足時は None。
    - `calc_volatility`：20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を制御。
    - `calc_value`：raw_financials から直近財務を結合して PER, ROE を計算（EPS が 0 / NULL の場合は PER を None）。  
    - いずれも DuckDB 接続を受け取り `prices_daily` / `raw_financials` のみを参照する設計。 (`src/kabusys/research/factor_research.py`)
  - 研究モジュール公開インターフェースを `src/kabusys/research/__init__.py` でまとめてエクスポート。

- DuckDB スキーマ定義（初期の DDL）
  - Raw レイヤーのテーブル定義を追加（`raw_prices`, `raw_financials`, `raw_news`, `raw_executions` の DDL を含むモジュール）。初期化用のスキーマモジュール実装。 (`src/kabusys/data/schema.py`)

### 変更 (Changed)
- （初回リリースのため該当なし。または内部設計・実装方針の明確化）
  - Research モジュールは外部ライブラリ（pandas 等）に依存しない方針で実装。
  - DuckDB を中心としたストレージ設計（Raw / Processed / Feature / Execution 層の方針がコメントで示されている）。

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS パーサに defusedxml を使用して XML インジェクション等の攻撃を防止。
- RSS フェッチにおいて以下の防御を実装:
  - 最大応答サイズ制限（MAX_RESPONSE_BYTES）と Gzip 展開後の再検査（Gzip bomb 対策）。
  - リダイレクト先の検証とプライベートアドレス拒否（SSRF 対策）。
  - URL スキーム検証（http/https のみ許可）。
- J-Quants クライアントでトークン/認証処理を厳格化（401 の自動リフレッシュは 1 回のみ）し、無限再帰を防止。

### 既知の注意点 / 設計メモ
- Research の関数群はパフォーマンスのため SQL ウィンドウ関数を多用しており、DuckDB のテーブル構造（`prices_daily`, `raw_financials` 等）に依存する。
- `.env` 自動ロードはプロジェクトルートの特定に __file__ を起点とするため、パッケージ配布後も CWD に依存せずに動作する想定。ただしプロジェクトルートが検出できない場合は自動ロードをスキップする。
- news_collector の記事 ID は URL 正規化に強く依存するため、外部で URL 正規化の仕様を変えると既存記事の重複判定に影響する可能性がある。

### 破壊的変更 (Breaking Changes)
- 初回リリースのため該当なし。

## 今後の想定（推奨）
- Strategy / Execution / Monitoring モジュールの実装拡充（現状はパッケージ構成のみ存在）。
- 単体テスト・統合テストの追加（特にネットワーク・DB 周りのモックテスト）。
- ドキュメント（使用例、DB マイグレーション手順、.env.example）の充実。

---

（注）本 CHANGELOG は提供されたソースコードを解析して推測した初回リリース向けの変更履歴です。実際のリリースノート作成時はコミット履歴・リリース日・担当者などの正確な情報で更新してください。
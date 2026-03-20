# Changelog

すべての注目すべき変更をこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠しています。

- リポジトリのバージョンは src/kabusys/__init__.py の __version__ に従っています。

## [Unreleased]

（現在のところ未リリースの変更はありません）

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買 / 研究プラットフォームのコア機能を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。公開 API: data, strategy, execution, monitoring（__all__）。

- 環境設定 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動読み込み機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 自動読み込みを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーが以下をサポート:
    - コメント行、先頭に export を含む行、クォート文字列（シンプルなエスケープ処理）、インラインコメント処理。
    - override と protected の概念により OS 環境変数を保護しつつ .env.local で上書き可能。
  - Settings クラスを追加し、必要な設定値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティ経由で提供。
  - 環境値検証:
    - KABUSYS_ENV は development/paper_trading/live のいずれかのみ許容。
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容。
  - デフォルトの DB パス設定（DUCKDB_PATH, SQLITE_PATH）を提供。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装（取得・保存機能）。
    - レート制限対応（120 req/min）: 固定間隔スロットリングを実装する RateLimiter。
    - 再試行・指数バックオフ（最大 3 回）とステータスコードに応じた扱い（408/429/5xx を再試行対象）。
    - 401 の場合はリフレッシュトークンで id_token を自動取得して 1 回リトライ（無限再帰防止）。
    - ページネーション対応で全件取得。
    - 取得時刻（fetched_at）を UTC で記録し、look-ahead bias のトレースを容易に。
  - fetch/save 系関数を追加:
    - fetch_daily_quotes / save_daily_quotes（raw_prices へ冪等保存、ON CONFLICT DO UPDATE）
    - fetch_financial_statements / save_financial_statements（raw_financials へ冪等保存）
    - fetch_market_calendar / save_market_calendar（market_calendar へ冪等保存）
  - 型変換ユーティリティ (_to_float, _to_int) を追加し、入力の堅牢化を実現。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを収集して raw_news に保存するモジュールを追加。
    - URL 正規化（トラッキングパラメータ除去・ソート・フラグメント削除・小文字化）を実装。
    - 記事 ID は正規化 URL の SHA-256 を利用して冪等性を確保。
    - defusedxml を使った XML パース（XML Bomb 等の防御）。
    - HTTP レスポンスサイズ上限（10 MB）やスキーム/ホスト等のチェックで SSRF / DoS を軽減。
    - バルク INSERT のチャンク処理で DB オーバーヘッドを抑制。
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。

- 研究用ファクター計算 (src/kabusys/research/*.py)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。
    - calc_value: 最新の財務データ（raw_financials）と当日株価から PER / ROE を計算。
    - 各関数は prices_daily / raw_financials のみ参照し、date/code 単位の dict リストを返す設計。
  - feature_exploration.py:
    - calc_forward_returns: 指定日から将来の終値までのリターン（任意ホライズン）をまとめて取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算する実装（同順位は平均ランク処理）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を算出。
    - rank ユーティリティを提供（同順位は平均ランク、丸め処理による ties 対応）。
  - research パッケージの公開 API を整備（calc_momentum, calc_volatility, calc_value, zscore_normalize 等の再エクスポート）。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features を実装:
    - research モジュールの生ファクター（momentum/volatility/value）を取得してマージ。
    - ユニバースフィルタを適用（株価 >= 300 円、20 日平均売買代金 >= 5 億円）。
    - 指定カラムを zscore 正規化（データ数が少ない場合は None で処理）。
    - Z スコアを ±3 でクリップして外れ値影響を抑制。
    - 日付単位で features テーブルへ置換（DELETE + INSERT をトランザクション内で実行し原子性を保証）。
    - 処理結果の upsert 件数を返却。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals を実装:
    - features / ai_scores / positions を参照して最終スコア（final_score）を計算。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI スコア）を計算するユーティリティを実装（シグモイド変換・平均化など）。
    - デフォルト重みを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザー重みは検証してマージ・再スケール。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数で検出）による BUY 抑制。
    - BUY シグナル閾値のデフォルトは 0.60。SELL（エグジット）条件としてストップロス（-8%）とスコア低下を実装。
    - SELL 優先ポリシー: SELL 対象は BUY 候補から除外し、ランクを再割り当て。
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）。
    - 生成したシグナル数（BUY + SELL）を返却。
  - 売り判定の追加注意:
    - トレーリングストップや時間決済は未実装（positions に peak_price / entry_date が必要）。該当箇所に TODO コメントあり。

### 変更 (Changed)
- N/A（初回リリースのため過去変更なし）

### 修正 (Fixed)
- N/A（初回リリースのため修正履歴なし）

### セキュリティ (Security)
- RSS パーサーに defusedxml を採用して XML 関連攻撃を緩和。
- ニュース収集で受信サイズ上限を設定しメモリ DoS を軽減。
- URL 正規化でトラッキングパラメータを除去し、記事 ID をハッシュ化して冪等性を確保。
- config の .env ロードで OS 環境変数を protected として上書きから保護。

### 既知の制限 / TODO
- signal_generator の一部エグジット条件（トレーリングストップ・時間決済）は未実装。positions テーブルの追加フィールドが必要。
- zscore_normalize は kabusys.data.stats に依存しているが、この CHANGELOG 作成時点の実装状況に応じて別途提供される想定。
- 一部のデータ取得 / 保存は外部 API（J-Quants）や DuckDB スキーマに依存しており、本体リリース前にスキーマ・運用手順の整備が必要。

---

参考: 本 CHANGELOG はコードベースからの仕様・実装内容を読み取り推測して作成しています。実際のリリースノート作成時は追加の変更点（ドキュメント、テスト、CI 設定等）を反映してください。
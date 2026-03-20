# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回リリース。本バージョンで追加された主要機能と設計上の要点を以下にまとめます。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの公開 API を定義（data, strategy, execution, monitoring）。
  - バージョン指定: 0.1.0。

- 環境設定/設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定値を自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）。
  - 読み込みの優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いをサポート）。
  - 上書きモードと保護キー（OS 環境変数を上書きしない）に対応したロード関数。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス等の設定プロパティを公開。値検証（KABUSYS_ENV/LOG_LEVEL の許容値チェック）を実装。

- Data: J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API から日足・財務データ・マーケットカレンダーを取得するクライアントを実装。
  - レート制限（120 req/min）を守る固定間隔の RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大 3 回。408/429/5xx 対象）。429 の場合は Retry-After を考慮。
  - 401 受信時にリフレッシュトークンで自動的に ID トークンを更新して再試行（1 回のみ）。
  - ページネーション対応で全レコードを取得する実装（fetch_* 系関数）。
  - DuckDB への保存関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - 保存は冪等（ON CONFLICT DO UPDATE）で上書き・更新を行う。
    - レコード変換ユーティリティ（_to_float, _to_int）を実装し不正データを安全に扱う。
  - fetched_at は UTC ISO8601 で記録し、データ取得時点をトレース可能に。

- Data: ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存するモジュールを実装（デフォルトソースに Yahoo Finance を設定）。
  - セキュリティ設計: defusedxml を用いて XML Bomb 等に対処、HTTP(S) スキームのみ許可、受信サイズ上限（10 MB）を設定。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント除去、クエリパラメータソート）により記事 ID を SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保。
  - テキスト前処理（URL 除去・空白正規化）と、バルク INSERT（チャンク処理）を実装。
  - DB への保存は ON CONFLICT DO NOTHING / トランザクションで行い挿入数を正確に返す方針。

- Research: ファクター計算・解析 (src/kabusys/research/*.py)
  - factor_research:
    - モメンタム（mom_1m, mom_3m, mom_6m, ma200_dev）、ボラティリティ（atr_20, atr_pct）、流動性（avg_turnover, volume_ratio）、バリュー（per, roe）を DuckDB の prices_daily / raw_financials から計算する関数を実装。
    - ウィンドウや必要データ不足時の取り扱いを明確にし、欠損は None を返す。
  - feature_exploration:
    - 将来リターン計算 (calc_forward_returns)：単一クエリで複数ホライズンのリターンを取得。
    - IC 計算 (calc_ic)：Spearman の ρ（ランク相関）を計算し、サンプル不足時は None を返す。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank ユーティリティ：同順位は平均ランクで処理（丸めで ties 検出漏れ防止）。
  - research パッケージの __all__ を整備。

- Strategy: 特徴量作成・シグナル生成 (src/kabusys/strategy/*.py)
  - feature_engineering.build_features:
    - research の生ファクターを取得（calc_momentum / calc_volatility / calc_value）、ユニバースフィルタ（最低株価300円、20日平均売買代金 5 億円）を適用。
    - 指定列を Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT）して冪等性を確保。トランザクション制御あり。
  - signal_generator.generate_signals:
    - features および ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアから final_score を計算（デフォルト重みを使用、ユーザ提供の重みは検証・正規化）。
    - シグモイド変換や欠損補完（コンポーネント欠損は中立 0.5）によりスコアを安定化。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数がある場合 BUY を抑制）。
    - BUY シグナル閾値（デフォルト 0.60）超過で BUY を生成、保有ポジションに対するエグジット判定（ストップロス -8% とスコア低下）で SELL を生成。
    - SELL 優先ポリシーを実装（SELL 対象は BUY から除外）、signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。
    - weights の不正値フィルタリングや合計再スケールを実装。

- その他
  - research と strategy の公開 API を __init__.py で整理。
  - execution パッケージ（発注ロジック）はプレースホルダ（空の __init__.py）として用意。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector: defusedxml の使用、受信サイズ制限、HTTP スキームチェックなどで外部入力に対する安全策を導入。
- jquants_client: トークンリフレッシュ時の無限再帰防止（allow_refresh フラグ）や 429 の Retry-After 優先利用などの堅牢化。

### 既知の制限 / 今後の課題 (Known issues / TODO)
- signal_generator のエグジット条件のうち「トレーリングストップ」や「時間決済（保有期間）」は positions テーブルの拡張（peak_price / entry_date 等）が必要で未実装。
- news_collector の RSS フェッチ周りでのネットワーク堅牢化（タイムアウトやエラーハンドリング拡張）は今後改善予定。
- モジュール間の単体テストが必要（特に DB に依存する部分はインテグレーションテスト推奨）。
- performance tuning: 大量データ時の DuckDB クエリ最適化および bulk 操作の最適化余地あり。

---

（注）本 CHANGELOG は提供されたコードベースから推測して作成しています。実装意図や外部仕様の細部は実際のドキュメント・設計資料を参照してください。
# Changelog

すべての変更は「Keep a Changelog」の形式に従います。  
このファイルはコードベースから推測した初回リリース向けの変更履歴です。

リリース日: 2026-03-20

## [0.1.0] - 2026-03-20

### 追加
- 基本パッケージ構成を追加
  - パッケージ名: kabusys（src/kabusys）
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
  - パブリック API: data, strategy, execution, monitoring を __all__ で公開

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能（プロジェクトルートを .git / pyproject.toml で検出）
  - .env パーサ（export プレフィックス、クォート対応、インラインコメント処理）
  - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 必須環境変数取得ヘルパー _require と Settings クラス（J-Quants / kabuAPI / Slack / DB パス / 環境 / ログレベル等）
  - 環境値検証（KABUSYS_ENV / LOG_LEVEL）

- データ取得・保存（src/kabusys/data）
  - J-Quants クライアント（src/kabusys/data/jquants_client.py）
    - API 呼び出しユーティリティ（JSON パース、ページネーション対応）
    - 固定間隔スロットリングによるレート制限制御（120 req/min）
    - リトライ（指数バックオフ、最大3回）、429 の Retry-After 尊重、408/429/5xx をリトライ対象に指定
    - 401 受信時の自動トークンリフレッシュ（1 回まで）と ID トークンキャッシュ
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB への保存関数（冪等性を担保する ON CONFLICT DO UPDATE）
      - save_daily_quotes → raw_prices
      - save_financial_statements → raw_financials
      - save_market_calendar → market_calendar
    - 入力変換ユーティリティ _to_float, _to_int（堅牢なパース）

  - ニュース収集（src/kabusys/data/news_collector.py）
    - RSS フィードからの収集ロジック（デフォルトソースに Yahoo Finance を含む）
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）
    - XML パースに defusedxml を使用してセキュリティ対策
    - 受信サイズ上限（10MB）・SSRF 対策意識の実装
    - 記事ID を正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性確保
    - raw_news / news_symbols への冪等保存（チャンク化バルク挿入、ON CONFLICT DO NOTHING）

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）を計算
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算
    - calc_value: raw_financials と当日株価から PER/ROE を計算（最新報告を取得）
    - DuckDB（prices_daily / raw_financials）を用いた SQL ベース実装

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算
    - calc_ic: スピアマンランク相関（Information Coefficient）計算
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）
    - rank: 同順位の平均ランクを扱うランク関数（丸め処理で ties の漏れを防止）
    - すべて標準ライブラリ + DuckDB のみで実装（pandas 等に依存しない）

  - research パッケージの再エクスポート（__init__）に主要関数を追加

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date)
    - research モジュールから生ファクターを取得（calc_momentum, calc_volatility, calc_value）
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）
    - 指定列の Z スコア正規化および ±3 でクリップ
    - 日付単位で features テーブルへ置換挿入（トランザクション＋バルク挿入で冪等）

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores をマージしてモメンタム / バリュー / ボラティリティ / 流動性 / ニュースのコンポーネントスコアを計算
    - シグモイド変換・欠損は中立値 0.5 で補完
    - デフォルト重みを定義し、ユーザー重みは検証（未知キーや不正値を無視）、合計が 1.0 でなければ再スケール
    - Bear レジーム判定（ai_scores の regime_score 平均が負でかつサンプル数閾値を満たす場合）
    - BUY: final_score >= threshold（Bear の場合は BUY を抑制）
    - SELL: ポジションに対するエグジット判定（ストップロス -8% / final_score < threshold）
    - SELL 優先ポリシー（SELL 銘柄を BUY から除外）、signals テーブルへ日付単位置換（トランザクションで原子性確保）
    - ログ出力・安全な重複処理と例外時の ROLLBACK を実装

### 変更（設計方針・実装ノート）
- ルックアヘッドバイアス対策を多くのモジュールで採用
  - データ取得時に fetched_at を UTC で記録
  - 特徴量・シグナル生成は target_date 時点のデータのみ参照する設計
- DuckDB を中心にデータパイプラインを構築（SQL と Python の組合せ）
- 外部 API 呼び出しの堅牢化（レート制御・リトライ・トークン管理・ページネーション）
- ロギングを広範に導入し警告・情報を出力することで運用時の可観測性を向上

### 既知の未実装 / 注意点
- signal_generator のエグジット条件において、以下は未実装（要 positions テーブルの拡張: peak_price / entry_date など）
  - トレーリングストップ（直近最高値からの比率）
  - 時間決済（保有 60 営業日超過）
- execution モジュールは初期状態では実装ファイルが空（発注ロジックは別途実装が必要）
- monitoring モジュール（__all__ に含まれるが実装ファイルは本差分に含まれていない可能性あり）

### 修正
- （初版のため該当なし）

### セキュリティ
- news_collector で defusedxml を採用し XML 関連の攻撃を緩和
- ニュース取得時の受信バイト上限・SSRF対策を実装

---

注:
- 本 CHANGELOG は提供されたコードベースから機能・設計意図を推測して作成したものであり、実際のコミット履歴ではありません。機能追加・修正の正確な履歴を作成するにはバージョン管理履歴（git log 等）を基にすることを推奨します。
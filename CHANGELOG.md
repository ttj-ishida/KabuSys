# Changelog

すべての notable な変更を記録します。本ファイルは Keep a Changelog の慣例に従っています。  
このリポジトリ初回リリース (v0.1.0) の内容はコードベースから推測して記載しています。

最新: Unreleased

## [Unreleased]
- （今後の変更をここに記載します）

## [0.1.0] - 2026-03-20
初回公開リリース。以下の主要機能・実装を含みます。

### 追加（Added）
- パッケージ基礎
  - パッケージルート: kabusys（src/kabusys）。バージョンは `__version__ = "0.1.0"`。
  - public API エクスポート: data, strategy, execution, monitoring（__all__）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を起点）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env の行パーサ（export 形式、クォート／エスケープ、インラインコメント処理に対応）。
  - 上書き制御と「保護された」OS 環境変数を考慮したロード（protected set）。
  - Settings クラス:
    - J-Quants や kabuAPI、Slack、DB パス等のプロパティを提供（必須キーは未設定時に ValueError）。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値のチェック）。
    - duckdb/sqlite のデフォルトパスを Path オブジェクトで返すユーティリティ。

- Data レイヤー（src/kabusys/data）
  - J-Quants API クライアント（jquants_client.py）
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装（_RateLimiter）。
    - 自動リトライ（指数バックオフ、最大3回）および特定ステータス（408/429/5xx）への対応。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
    - ページネーション対応のフェッチ（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）:
      - fetched_at を UTC 形式で記録。
      - 入力検証（主キー欠損行のスキップ）・警告ログ。
      - ON CONFLICT DO UPDATE による冪等保存。
    - 型変換ユーティリティ（_to_float / _to_int）で堅牢な変換を実装。
  - ニュース収集（news_collector.py）
    - RSS フィード収集の基本機能と前処理ロジック（デフォルトソースに Yahoo Finance を含む）。
    - URL 正規化機能（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント削除、クエリソート）。
    - 受信最大バイト数制限（10 MB）やバルク INSERT チャンク化等の DoS 対策方針が記述。
    - 記事ID のハッシュ化（設計方針）による冪等性の確保（コメントに記載）。

- Research レイヤー（src/kabusys/research）
  - ファクター計算（factor_research.py）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）を SQL ウィンドウ関数で計算。
    - Volatility（20日 ATR・相対 ATR・平均売買代金・出来高比）を計算。
    - Value（PER、ROE）を raw_financials と prices_daily から結合して計算。
    - 日付スキャン範囲やウィンドウの設計（スキャンバッファ、営業日近似）に関する設計注釈。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト 1,5,21）に対応。単一クエリで取得、存在しない場合は None。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンの ρ をランク付けで計算。データ不足（<3 レコード）時は None。
    - 統計サマリー（factor_summary）とランク関数（rank）。

- Strategy レイヤー（src/kabusys/strategy）
  - 特徴量エンジニアリング（feature_engineering.py）
    - research の生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムの Z スコア正規化（data.stats.zscore_normalize を利用）と ±3 でのクリップ。
    - features テーブルへトランザクション＋日付単位の置換（冪等）で挿入。
  - シグナル生成（signal_generator.py）
    - features と ai_scores を統合して各コンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - Sigmoid 変換、欠損を中立 0.5 で補完、重み付け（デフォルトの重みを参照）→ final_score を計算。
    - Bear レジーム検知（ai_scores の regime_score 平均 < 0 かつサンプル数閾値）で BUY を抑制。
    - BUY 条件（閾値 0.60 デフォルト）、SELL 条件（ストップロス -8%、スコア低下）を実装。
    - positions / prices を参照した SELL 判定、価格欠損時の判定スキップやログ出力。
    - signals テーブルへトランザクション＋日付単位の置換（冪等）で挿入。

- DB / トランザクション設計
  - DuckDB を前提とした SQL 実装（window functions を多用）。
  - 日付単位の置換（DELETE → INSERT）をトランザクションで囲い、原子性（COMMIT / ROLLBACK）の保証。
  - 大量挿入を executemany / チャンクで扱う方針。

### 変更（Changed）
- 初期リリースのため該当なし（最初の実装です）。

### 修正（Fixed）
- 初期リリースのため該当なし。

### セキュリティ（Security）
- ニュースパーサ: defusedxml を利用する設計となっており XML 関連の攻撃（XML bomb 等）への対策を明示。
- ニュース URL の検証・正規化、トラッキングパラメータ除去、受信サイズ制限、HTTP スキームの制限等で SSRF / メモリ DoS 緩和を考慮。
- J-Quants クライアントにおけるネットワークエラーや HTTP エラーに対する明示的なハンドリングとログ出力（リトライ・バックオフ）。

### 注意事項 / 互換性（Notes）
- Python の型注釈で | を使用しているため、Python 3.10 以上が想定されます。
- DuckDB に依存する SQL 実装（WINDOW 関数や ROW_NUMBER）を使用しており、DuckDB 環境での実行を前提とします。
- 一部の未実装・将来実装予定の機能（factor_research の一部指標、signal_generator の一部エグジット条件やトレーリングストップ等）はコメントで言及されています。
- .env パーサは多くのケースに対応しますが、複雑な .env 構成（多行クォート等）では事前の検証を推奨します。

---

開発者向け: 実装の多くは設計方針・安全性・冪等性を重視して記述されています。運用前に実データでの統合テスト（特に DB スキーマ・テーブル名・主キー制約・外部サービスの認証情報）を必ず行ってください。
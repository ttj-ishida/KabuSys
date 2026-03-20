# Changelog

すべての重要な変更点をここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠します。

現行バージョン: 0.1.0

## [Unreleased]
今後の予定・改善点（コード内コメントから推測）
- エグジットロジックの強化
  - トレーリングストップ（peak_price が必要）：positions テーブルに peak_price / entry_date を追加して実装予定
  - 保有期間に基づく時間決済（60 営業日超過）実装予定
- データ取得／保存の拡張
  - 財務指標（PBR・配当利回り）などバリュー指標の追加
- ニュース収集の堅牢化・拡張
  - RSS ソース追加、自然言語処理によるニュース分類やシンボル抽出の精度向上
- テスト・ドキュメント整備
  - 各モジュールのユニットテスト充実、API 使用例の追加

---

## [0.1.0] - 2026-03-20

Added
- パッケージの初期リリースとして以下の主要機能を追加
  - パッケージ構成
    - kabusys パッケージ。主要サブパッケージ: data, research, strategy, execution, monitoring（__all__ に公開）
    - バージョン定義: 0.1.0
  - 環境変数・設定管理（kabusys.config）
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）
    - 読み込み順序: OS 環境変数 > .env.local（override）> .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）
    - .env 行パーサ実装（export 形式、シングル/ダブルクォート、エスケープ、行内コメントの考慮）
    - Settings クラス（プロパティベース）: J-Quants / kabu API / Slack / DB パス / 環境モード・ログレベルの検証（許容値チェック）
  - データ取得・保存（kabusys.data.jquants_client）
    - J-Quants API クライアント（ページネーション対応）
    - 固定間隔スロットリングによるレート制御（120 req/min）
    - リトライ（最大 3 回）＋指数バックオフ、HTTP 429 の Retry-After 尊重
    - 401 受信時はリフレッシュトークンを用いた id_token 自動リフレッシュを 1 回だけ実行
    - id_token のモジュールキャッシュ実装（ページネーション間で共有）
    - fetch_* 系関数: daily_quotes, financial_statements, market_calendar（JSON パースとログ）
    - save_* 系関数: raw_prices / raw_financials / market_calendar への冪等保存（ON CONFLICT DO UPDATE）
    - レコード変換ユーティリティ: _to_float / _to_int（耐障害性に配慮）
  - ニュース収集（kabusys.data.news_collector）
    - RSS 取得・パース・前処理パイプライン（デフォルトに Yahoo Finance のカテゴリ RSS を含む）
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去、小文字化）
    - セキュリティ対策:
      - defusedxml を用いた XML パース（XML Bomb 等の緩和）
      - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を抑制
      - URL 正規化／チェックによる SSRF 対策方針（コメントに明記）
    - 記事ID の決定に SHA-256 ハッシュ（正規化後）を用いることで冪等性を確保
    - DB へバルク INSERT（チャンク化）および ON CONFLICT / INSERT RETURNING を想定した設計
  - 研究モジュール（kabusys.research）
    - ファクター計算（kabusys.research.factor_research）
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日窓のチェック）
      - calc_volatility: atr_20 / atr_pct、avg_turnover、volume_ratio（20 日窓）
      - calc_value: per / roe（raw_financials と当日の価格を組み合わせ）
      - SQL を用いた高速集計（DuckDB 前提）、欠測時は None を返す設計
    - 特徴量探索（kabusys.research.feature_exploration）
      - calc_forward_returns: 将来リターン（複数ホライズン）を一括 SQL で取得
      - calc_ic: スピアマンランク相関（ランク化/タイ同順位の平均ランク処理）
      - factor_summary: count/mean/std/min/max/median の算出
      - rank: ランク変換ユーティリティ（丸めで ties を安定化）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - build_features:
      - research モジュールから原始ファクターを取得し統合
      - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）
      - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ
      - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT、ロールバックハンドリング）
      - ルックアヘッドバイアス回避の設計（target_date 時点のデータのみ使用）
  - シグナル生成（kabusys.strategy.signal_generator）
    - generate_signals:
      - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
      - コンポーネントごとの算出ロジック（シグモイド変換や PER の逆数近似など）
      - デフォルト重みを用意し、ユーザ指定 weights の検証・マージ・再スケーリングを実施
      - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル閾値を満たす場合）
      - BUY シグナルは閾値（デフォルト 0.60）で生成、Bear では BUY を抑制
      - SELL（エグジット）判定:
        - ストップロス（終値 / avg_price - 1 < -8%）を最優先
        - final_score が閾値未満の場合は SELL
        - 価格欠損時は SELL 判定をスキップ（誤クローズ防止）
      - signals テーブルへ日付単位置換（トランザクション + バルク挿入）
  - ロギングと安全性
    - 各処理で適切なログ出力（info/warning/debug）を追加
    - トランザクションの失敗時に ROLLBACK を試行し、失敗ログを記録

Changed
- 初回リリースのため、過去変更履歴はなし（すべて追加として提供）

Fixed
- .env パーサやデータパース処理での多くの実運用上の例外ケースを考慮:
  - export プレフィックス、クォート内のエスケープ、行内コメントの扱いを実装
  - raw API レスポンスの必須キー欠損行はスキップして警告を出力（save_* 系）

Security
- ニュース収集で defusedxml を利用し XML 攻撃を緩和
- レスポンスサイズ制限や URL 正規化により SSRF / メモリ DoS のリスクを軽減
- API クライアントで HTTPS を前提とした実装、トークン自動更新時の無限再帰防止

Notes / Known limitations
- signal_generator の一部機能は未実装（コード内コメント参照）
  - トレーリングストップ / 時間決済は positions テーブルに追加情報が必要
- バリュー指標の一部（PBR・配当利回り）は現バージョンでは未実装
- AI ニューススコアは中立（0.5）で補完する設計のため、AI スコア取得タイミングによっては影響がある
- DuckDB スキーマ（テーブル定義）はこの CHANGELOG に含まず、利用前に適切なスキーマを作成する必要がある

---

貢献・報告
- バグ報告や改善提案はリポジトリの Issue を通じてお願いします。
# CHANGELOG

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠します。

全般:
- このリポジトリは日本株自動売買システム "KabuSys" の初期実装を含みます。
- パッケージバージョン: 0.1.0

## [Unreleased]

（現在の変更はまだリリースされていません）

---

## [0.1.0] - 2026-03-19

初回リリース — 基本的なデータ収集、ファクター計算、特徴量エンジニアリング、シグナル生成、および設定管理を実装。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ （モジュール公開: data, strategy, execution, monitoring）。
  - バージョン: 0.1.0。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - クォート無しの値でのインラインコメント処理（直前が空白またはタブの `#` をコメントとみなす）。
  - Settings クラス:
    - 必須の環境変数取得メソッド（設定されていない場合は ValueError を送出）。
    - J-Quants / kabu ステーション / Slack 等の各種設定プロパティ。
    - デフォルト DB パス（DuckDB / SQLite）と Path 返却。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL（DEBUG/INFO/...）の検証プロパティ。
    - is_live / is_paper / is_dev 便宜プロパティ。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアント実装:
    - 固定間隔スロットリングによるレート制限 (120 req/min) 制御（内部 RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回）。HTTP 429 の Retry-After を考慮。
    - 401 受信時はリフレッシュトークンを用いて ID トークン自動更新を行い 1 回リトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - 保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
      - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE または DO NOTHING）。
      - fetched_at を UTC で記録（look-ahead bias をトレース可能にするため）。
      - PK 欠損行はスキップし、スキップ数を警告ログ出力。
    - 型変換ユーティリティ: _to_float / _to_int（入力の安全なパース）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集と raw_news 保存の実装（デフォルトソース: Yahoo Finance）。
  - セキュリティ対策:
    - defusedxml を利用して XML 攻撃を防御。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）。
    - URL 正規化: トラッキングパラメータ（utm_* など）削除、スキーム/ホスト小文字化、フラグメント削除、クエリキーソート。
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保。
    - HTTP/HTTPS スキームの許可など SSRF を考慮した入力検証（実装方針に基づく）。
  - バルク INSERT のチャンク処理で SQL 長やパラメータ数を抑制。

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: mom_1m / mom_3m / mom_6m, ma200_dev（200 日窓の扱い、データ不足時は None）。
    - calc_volatility: 20 日 ATR (atr_20) / 相対ATR(atr_pct)、20 日平均売買代金 (avg_turnover)、出来高比率 (volume_ratio)。true_range 計算で NULL 伝播を正確に制御。
    - calc_value: raw_financials から直近財務データを取得して PER / ROE を算出（EPS が 0 または欠損の場合は None）。
    - 各関数は prices_daily / raw_financials のみ参照し外部 API に依存しない。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得（パフォーマンス最適化）。
    - calc_ic: スピアマンのランク相関（IC）計算（有効サンプル < 3 の場合は None）。
    - rank / factor_summary: 同順位は平均ランク処理、基本統計量（count/mean/std/min/max/median）計算。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装:
    - research モジュールの calc_momentum / calc_volatility / calc_value を利用して生ファクターを取得。
    - ユニバースフィルタ: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
    - 指定カラムを Z スコアで正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT、トランザクションにより原子性を保証）。
    - target_date 時点のデータのみを使用しルックアヘッドバイアスを防止。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装:
    - features と ai_scores を統合し、モメンタム / バリュー / ボラティリティ / 流動性 / ニュースのコンポーネントスコアを計算。
    - コンポーネント計算:
      - モメンタム: momentum_20/60/ma200_dev のシグモイド平均。
      - バリュー: PER を 20 を基準に 1/(1+per/20) でスケール（per が無効時は None）。
      - ボラティリティ: atr_pct の Z スコアを反転してシグモイド。
      - 流動性: volume_ratio のシグモイド。
    - AI スコア: ai_score をシグモイド変換で組み込み（未登録は中立）。
    - 重み処理:
      - デフォルト重みを用意（momentum 0.4, value 0.2, volatility 0.15, liquidity 0.15, news 0.1）。
      - ユーザ指定 weights は検証（未知キー・非数値・負値等は無視）後に合計が 1.0 になるよう再スケール。
    - Bear レジーム検知: ai_scores の regime_score の平均が負（かつサンプル数 >= 3）である場合、BUY シグナルを抑制。
    - BUY 生成: final_score >= threshold（デフォルト 0.60）を満たす銘柄に BUY（Bear 時は抑制）。
    - SELL 生成（エグジット判定）:
      - ストップロス: 終値/avg_price - 1 <= -8%（最優先）。
      - スコア低下: final_score が threshold 未満。
      - 価格欠損時は SELL 判定をスキップして誤クローズを回避。
      - 未実装（将来の実装予定）: トレーリングストップ、時間決済（positions テーブルの拡張が必要）。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY ランクを再付与。
    - signals テーブルへ日付単位の置換（トランザクションで原子性を保証）。
    - ログ出力で処理状況（BUY/SELL 数、日付等）を記録。

### Security
- RSS パーシングに defusedxml を使用して XML による攻撃を軽減。
- J-Quants API へのリクエストにおいてトークン管理を行い、認証失敗時の自動リフレッシュで機密情報の扱いを想定。
- .env の読み込みはプロジェクトルートを基準に行い、OS 環境変数の保護（上書き不可）を実装。

### Notes / Implementation details
- 多くの DB 操作で「日付単位の置換（DELETE + bulk INSERT）」を採用し、トランザクションで原子性を確保しているため冪等性が高い設計。
- DuckDB を前提とした SQL クエリ実装（ウィンドウ関数を多用）。research モジュールは追加ライブラリに依存しない設計（標準ライブラリのみ）。
- ログ（logger）を各モジュールに導入して運用時の可観測性を確保。
- いくつかの箇所で「未実装の拡張点」をコメントで明示（例: トレーリングストップ、positions の peak_price/entry_date 管理など）。

### Breaking Changes
- 初回リリースのため特に該当なし。

---

今後の予定（例）
- positions テーブルの拡張（peak_price / entry_date 等）によるトレーリングストップや時間決済の実装。
- news_collector: 実際の RSS パースロジックの拡充（複数ソース対応、記事→銘柄マッチングの強化）。
- テスト追加（ユニットテスト・統合テスト）、CI の導入。
- ドキュメント（StrategyModel.md / DataPlatform.md）との整合性チェックとサンプル運用手順の追加。

以上。
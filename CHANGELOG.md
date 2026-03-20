# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。  

現在のバージョン: 0.1.0 — 初回リリース（2026-03-20）

## [Unreleased]
N/A

## [0.1.0] - 2026-03-20
初回公開リリース。日本株自動売買システムのコアライブラリを実装しました。以下は主要な追加点・設計方針・実装詳細の抜粋です。

### 追加 (Added)
- パッケージ基本情報
  - kabusys パッケージを追加。バージョンは `0.1.0`。
  - 公開 API: `kabusys.strategy.build_features`, `kabusys.strategy.generate_signals` などを __all__ で公開。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む `Settings` クラスを提供。
  - 自動 .env ロード機能:
    - プロジェクトルートを `.git` または `pyproject.toml` から探索して検出。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサーの強化:
    - `export KEY=val` 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの取り扱い。
    - コメント判定はクォートの有無に応じて厳密に処理。
  - 必須環境変数取得のユーティリティ `_require` と各種プロパティ（J-Quants トークン、Kabu API パスワード、Slack トークン/チャンネル、DB パス、環境/ログレベル検証等）。

- データ取得・保存 (kabusys.data)
  - J-Quants クライアント (jquants_client)
    - API 通信ユーティリティ `_request` を実装（JSON デコード、例外処理、最大リトライ）。
    - レート制御: 固定間隔スロットリングで 120 req/min 制限を遵守する RateLimiter を実装。
    - 再試行ロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx に対してリトライ、429 の場合は `Retry-After` を考慮。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）を実装。
    - ページネーション対応（`pagination_key` ベース）と ID トークンのモジュールレベルキャッシュ共有。
    - データ保存ユーティリティ:
      - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`：DuckDB への冪等保存（ON CONFLICT DO UPDATE）を実装。
      - 型変換ユーティリティ `_to_float`, `_to_int` を実装し、各種入力の安全な変換を保証。
  - ニュース収集モジュール (news_collector)
    - RSS フィードから記事を収集する処理基盤を追加（デフォルトソースとして Yahoo Japan のビジネス RSS を設定）。
    - セキュリティ／堅牢性対策:
      - defusedxml を利用して XML 攻撃を回避。
      - 受信サイズ上限（10MB）や URL 正規化（トラッキングパラメータ除去、スキーム/ホスト正規化、断片除去）による SSRF / DoS 緩和。
      - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）などで冪等性を担保。
    - バルク INSERT のチャンク化実装により DB への過負荷を抑制（チャンクサイズを定義）。
    - テキスト前処理（URL 除去・空白正規化）等の整形処理を実装。

- リサーチ（研究）モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算（200 日 MA のデータ不足ハンドリング含む）。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）計算（ATR の NULL 伝播制御、窓サイズ検査）。
    - Value（per, roe）計算（raw_financials から最新の報告日を取得して prices と結合）。
    - DuckDB のウィンドウ関数/LEAD/LAG を利用した効率的な実装。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト [1,5,21]）の一括取得、営業日欠損へのバッファ処理。
    - IC（Information Coefficient）計算 (calc_ic)：Spearman の順位相関（ランクの同順位扱いは平均ランクで処理）、有効サンプル数 3 未満は None を返す。
    - factor_summary と rank ユーティリティ（基本統計量・中央値等の計算を純粋 Python で実装）。
  - zscore_normalize は kabusys.data.stats から利用可能（リサーチモジュールから再エクスポート）。

- 戦略（Strategy）モジュール (kabusys.strategy)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research の生ファクターを統合し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - Z スコア正規化（指定列）、±3 でクリップし features テーブルへ日付単位の置換（BEGIN/COMMIT/ROLLBACK によるトランザクション）で冪等性を保証。
    - 欠損や非有限値の扱いに注意した実装。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - デフォルト重みと閾値（weights デフォルト、threshold デフォルト 0.60）。ユーザー指定 weights のバリデーションと再スケーリング処理を実装。
    - シグモイド変換、欠損成分は中立値 0.5 で補完するポリシーを採用（欠損銘柄が不当に低評価されないように）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、サンプル数閾値あり）で BUY シグナルを抑制。
    - BUY シグナルは final_score >= threshold、SELL シグナルはストップロス（-8%）とスコア低下を適用。SELL は BUY より優先。
    - signals テーブルへの日付単位置換をトランザクションで実施し冪等性を維持。
    - 未実装の拡張点（ドキュメント記載）:
      - トレーリングストップ（peak_price/entry_date が positions に必要）、時間決済（保有 60 営業日超）などは将来対応予定。

### 変更 (Changed)
- （初版のため該当なし）設計方針や実装注釈を各モジュールにドキュメントとして同梱。

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- XML パースに defusedxml を利用し、RSS フィード処理における XML 攻撃リスクを軽減。
- news_collector において受信サイズ上限を設け、トラッキングパラメータ除去やスキーム/ホスト正規化で SSRF/不正 URL のリスクを低減。
- J-Quants クライアントは 401/429 を適切に扱い、Retry-After を尊重することで DoS を緩和。

### 既知の制約 / 未実装項目
- signal_generator 内の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルの情報（peak_price, entry_date 等）が未整備のため未実装。ドキュメントにて将来対応を示唆。
- news_collector の記事→銘柄紐付け（news_symbols）処理や INSERT RETURNING による正確な挿入件数の取得は設計方針で言及されているが、環境依存での DB 実装詳細に注意が必要。
- 単体テストや統合テストの記述はリポジトリ内に含まれていない（テスト環境の設定は今後整備予定）。

---

ご不明点や補足してほしい項目があれば、どのモジュールの変更履歴を詳細化するか指示してください。必要に応じてセクションの分割や英語併記も可能です。
# Changelog

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このプロジェクトの初回リリースとして v0.1.0 を作成しました。

## [0.1.0] - 2026-03-27

### 追加
- 初期パッケージ「kabusys」を追加
  - パッケージバージョン: 0.1.0
  - パッケージ説明: 日本株自動売買システムのコアライブラリ

- 環境設定/ローディング機能（kabusys.config）
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込み
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動探索（CWD 非依存）
  - .env 解析強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - クォートなし時のインラインコメント判定（直前が空白/タブの場合のみ）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 上書きロジック: OS 環境変数を保護する protected オプション
  - Settings クラス:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供
    - env（development, paper_trading, live）および LOG_LEVEL の検証
    - duckdb/sqlite のデフォルトパスを提供
    - is_live / is_paper / is_dev の便宜プロパティ

- AI 関連モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを算出して ai_scores テーブルへ保存
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）
    - バッチ処理: 最大 20 銘柄/回、1 銘柄あたりの記事数・文字数上限を設ける（過大入力対策）
    - レスポンスバリデーション: JSON 構造・型チェック・未知コードの無視・スコアクリップ（±1.0）
    - リトライ: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ
    - フェイルセーフ: API 失敗やパース失敗はスキップして処理継続（例外を上げない）
    - DuckDB 互換性考慮: executemany に空リストを渡さない等の保護
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次でレジーム（bull/neutral/bear）を判定
    - MA200 比率計算（target_date 未満のデータのみ使用してルックアヘッド防止）
    - マクロニュース抽出: 指定キーワードにマッチする raw_news タイトル（最大 20 件）
    - OpenAI 呼び出しは専用実装（ニュース NLP モジュールとは共有しない）
    - リトライ・フェイルセーフ: API 全失敗時は macro_sentiment=0.0 として継続
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行う
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）を返す

- Data（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを使った営業日判定/取得ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバック（祝日データ未取得時の一貫性保持）
    - 最大探索範囲を設定して無限ループを回避
    - 夜間バッチ calendar_update_job(conn, lookahead_days=90): J-Quants API から差分取得して保存、バックフィルや健全性チェックを実装
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・保存・品質チェック（quality モジュールとの連携）を行う設計
    - ETLResult データクラスを提供（kabusys.data.etl から再エクスポート）
    - 最終取得日の算出、backfill のデフォルト（3日）、カレンダー先読み等の制御変数を実装
    - DB 存在チェックや MAX 日付取得ユーティリティを提供

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200 日 MA に対する乖離）
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等
    - Value: PER, ROE（raw_financials から最新レコードを取得して計算）
    - DuckDB による SQL ベースの実装、結果は (date, code) をキーとした辞書リストで返却
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン算出（calc_forward_returns）、任意ホライズン対応（例: 1,5,21 日）
    - IC（Information Coefficient）算出（スピアマン ランク相関）
    - ランク化ユーティリティ（rank）：同順位は平均ランク、丸め処理で ties 対策
    - ファクター統計サマリー（count/mean/std/min/max/median）
    - pandas 等の外部依存を避け、標準ライブラリと DuckDB のみで実装

- 監視・ユーティリティ等
  - モジュール公開リスト整備（__all__）
  - ロギングや警告・例外ハンドリングを各モジュールで整備（ROLLBACK 失敗時の警告等）

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 非推奨
- （初回リリースのため該当なし）

### セキュリティ
- 環境変数ロード時に OS 環境変数を保護する protected set を導入（.env による上書きを制御）
- 必須環境変数は _require() で明示的にチェックして不足時に早期エラーを出力

### 注意事項 / 既知の制約
- DuckDB スキーマ（tables: prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が前提となる。実行前に適切なテーブル定義とデータを用意してください。
- OpenAI API 依存箇所は API キー（api_key 引数または環境変数 OPENAI_API_KEY）を必要とします。API レスポンス形式は JSON Mode を期待しています。
- 一部実装は J-Quants クライアント（kabusys.data.jquants_client）への依存があるが、該当クライアント実装はこの差分には含まれていません。
- news_nlp / regime_detector は外部 API 呼び出しのためレート制限やコストが発生します。運用時は注意してください。

---

今後のリリースでは、テストカバレッジ強化、エラーハンドリングの追加改善、さらに多くのファクター/指標の実装やパフォーマンス最適化を予定しています。
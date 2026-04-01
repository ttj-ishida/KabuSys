CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
（訳注: この CHANGELOG は与えられたコードベースの内容から推測して作成しています。）

[Unreleased]
------------

- （現時点のスナップショットでは未リリースの変更はありません）

[0.1.0] - 2026-04-01
-------------------

Added
- 初期リリース。日本株自動売買 / データ分析基盤「kabusys」のコア機能を実装。
  - パッケージ公開情報
    - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
    - パッケージ API: data, strategy, execution, monitoring を __all__ で公開（monitoring 等は将来的に拡張想定）
  - 環境設定 / 読み込みロジック（src/kabusys/config.py）
    - .env および .env.local をプロジェクトルート（.git / pyproject.toml を基準）から自動ロード
    - OS 環境変数を保護する protected 上書き制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応
    - .env の行パーサは以下をサポート/考慮:
      - 空行・コメント（#）の無視、export KEY=val 形式の対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理
      - クォートなしの場合のインラインコメント取り扱い（# の前がスペース/タブならコメント）
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）等のプロパティを取得可能
    - 環境変数未設定時には明確な ValueError を送出する必須取得ヘルパーを提供
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を銘柄ごとに集約して OpenAI（gpt-4o-mini、JSON mode）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込み
    - チャンク処理: 最大バッチサイズ 20 銘柄（_BATCH_SIZE）
    - 1 銘柄あたり最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
    - リトライ: 429（RateLimit）・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ（最大回数設定）
    - レスポンス検証: JSON のパース/構造検証・未知コードの無視・スコアの ±1.0 クリップ
    - フェイルセーフ: API 失敗やパース失敗時は例外を投げず該当チャンク/銘柄をスキップして処理継続
    - テスト容易性: _call_openai_api を unittest.mock.patch で差し替え可能
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で market_regime を算出・書き込み
    - LLM（gpt-4o-mini）呼び出しは独立実装。最大リトライ・バックオフ・API 失敗時のマクロスコア 0.0 フォールバックを実装
    - ルックアヘッドバイアス対策: datetime.today() を参照せず、prices_daily クエリで target_date 未満を使用
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）
  - 研究用ファクター計算（src/kabusys/research/）
    - factor_research.py:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足は None。
      - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。必要行数に満たない場合は None。
      - calc_value: raw_financials から最新財務を取得し PER/ROE を計算（PBR・配当利回りは未実装と明記）
    - feature_exploration.py:
      - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得（LEAD を使用）
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を算出（有効レコードが 3 未満なら None）
      - rank, factor_summary: ランク変換（同順位は平均ランク）や基本統計量集計を標準ライブラリのみで実装
    - 研究 API は DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照（本番発注等とは独立）
  - データプラットフォーム（src/kabusys/data/）
    - calendar_management.py:
      - 市場カレンダー管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装
      - DB の market_calendar が未登録時は曜日（平日）ベースのフォールバックを一貫して使用
      - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックあり）
    - pipeline.py / etl.py:
      - ETLResult データクラスを定義し etl モジュールで公開（ETL の取得数・保存数・品質問題・エラーを集計）
      - 差分更新、バックフィル、品質チェック（quality モジュールと連携）などの設計を反映
  - DuckDB を主要なローカル分析 DB として利用。DuckDB のバージョン依存（executemany の空リスト制約等）を考慮した実装

Changed
- （初回リリースのため履歴なし）

Fixed
- （初回リリースのため履歴なし）

Known limitations / Notes
- calc_value(): PBR・配当利回りは未実装（コード中に明記）
- 一部モジュールは外部設定（OpenAI API キー、J-Quants トークン、Slack トークンなど）を環境変数に依存。必須環境変数が未設定だと ValueError を送出する設計
- OpenAI 呼び出しは gpt-4o-mini を前提としている（モデル名称は定数で管理）
- news_nlp / regime_detector ともにレスポンスのパース失敗や API 障害時は「安全側」のフォールバック（スコア 0 やスキップ）を行い、全体処理が停止しないようにしている
- DuckDB の日付/型戻り値や executemany の挙動に対する互換性考慮がある（実行環境の DuckDB バージョンに依存する可能性あり）

作者・貢献者
- この CHANGELOG は提供されたソースコードから推測して作成しています。実際のリリースノート作成時は変更者自身による検証・補足を推奨します。
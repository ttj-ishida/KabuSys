Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
------------

- （現在のコードベースでは未リリースの作業はありません）

[0.1.0] - 2026-03-29
-------------------

Added
- 基本パッケージ情報
  - パッケージ version を 0.1.0 に設定（src/kabusys/__init__.py）。
  - 主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。CWD に依存しないため配布後も安定して動作。
  - export KEY=val 形式やシングル/ダブルクォート・バックスラッシュエスケープ・行末コメントなど実務で発生する .env の多様な書式に対応するパーサを実装。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テストでの利用想定）。
  - Settings クラスによる型付きプロパティを提供（J-Quants / kabu API / Slack / DB パス / システム設定等）。
  - KABUSYS_ENV / LOG_LEVEL の値チェックとフラグ（development, paper_trading, live 等）、DB パス（duckdb/sqlite）のデフォルト値設定。
  - 必須環境変数未設定時にわかりやすいエラーを送出する _require ヘルパー。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - score_news: raw_news と news_symbols を読んで銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントスコアを取得して ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST 相当）を calc_news_window として提供。
  - 1銘柄あたり記事数/文字数の上限（トークン肥大化対策）を実装（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - 銘柄ごと最大 20 件単位でのバッチ送信、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ処理を実装。
  - レスポンス検証ロジック（JSON パース耐性、results リスト・code/score の検証、スコアの数値変換および ±1.0 クリップ）を実装。
  - 書き込みは部分失敗時に既存データを保護するため、取得済みコードのみ DELETE → INSERT の冪等処理を行う（DuckDB 互換性考慮: executemany に対する空リスト回避）。
  - テスト容易性のために OpenAI 呼び出し箇所は _call_openai_api を経由し、unittest.mock.patch による差し替えを想定。
  - API キーは引数 api_key から注入可能（None の場合は環境変数 OPENAI_API_KEY を使用）。未設定時は ValueError を送出。

- マーケットレジーム判定（src/kabusys/ai/regime_detector.py）
  - score_regime: ETF コード 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次で冪等書き込みする機能を実装。
  - ma200_ratio 計算（target_date 未満のデータのみ参照し ルックアヘッドを防止）、データ不足時は中立（1.0）を返すフェイルセーフ。
  - マクロニュースは raw_news からマクロキーワードでフィルタして取得し、LLM に投げて -1.0〜1.0 の macro_sentiment を取得。API 失敗時は macro_sentiment=0.0 にフォールバックし例外を上げない。
  - OpenAI 呼び出しは専用の内部実装を使用し、news_nlp とは意図的に共有しない設計（モジュール結合低減）。
  - 書き込みは BEGIN/DELETE/INSERT/COMMIT のトランザクションで冪等処理。書き込み失敗時は ROLLBACK を試み上位へ例外を伝播する。

- データプラットフォーム / カレンダー（src/kabusys/data/calendar_management.py）
  - JPX マーケットカレンダーの管理機能を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
  - market_calendar テーブルが未取得/部分取得の場合は曜日ベースのフォールバックを行う設計（DB 登録値優先、未登録日はフォールバックで一貫性保持）。
  - カレンダー更新バッチ calendar_update_job を実装。J-Quants API クライアント経由で差分取得し save_market_calendar により冪等保存。バックフィルと健全性チェック（未来日異常検出）を実装。
  - 最大探索日数やバックフィル範囲などの定数による安全対策を導入。

- ETL / パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
  - ETLResult データクラスを導入し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を構造化して返す仕組みを提供。
  - 差分更新・バックフィル・品質チェックの方針を示すユーティリティ実装（テーブル存在チェック、最大日付取得など）。
  - data.etl モジュールで ETLResult を再エクスポート。

- Research（因子計算・特徴量解析）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離などを DuckDB のウィンドウ関数で計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金・出来高比率を計算。
    - calc_value: raw_financials から直近財務データを取得して PER / ROE を計算（EPS が 0/欠損時は None）。
    - いずれの関数も prices_daily / raw_financials のみ参照し外部 API へはアクセスしない設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを効率的に一括取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。欠損や同順位（ties）も扱う。
    - rank: 平均ランク（同順位は平均ランク）を計算。丸めによる ties 検出漏れ対策を実装。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを実装。
    - pandas 等外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

- その他
  - 各モジュールで詳細なログ出力を追加（debug/info/warning）し、障害時のトレースとフォールバックを分かりやすくした。
  - OpenAI 連携箇所は API キー注入可、テスト時の差し替えポイント（_call_openai_api）を明示しておりユニットテスト作成を意識した設計。
  - DuckDB に関する互換性配慮（executemany の空パラメータ回避、日付値の変換ユーティリティ等）を導入。

Changed
- 初回リリースのため該当項目なし。

Fixed
- 初回リリースのため該当項目なし。

Security
- 特記事項なし。

Notes / 実装上の設計判断（重要）
- AI モジュール（news_nlp, regime_detector）はルックアヘッドバイアスを避けるため date.today()/datetime.today() を参照せず、target_date を明示的に受け取る設計になっています。運用時は必ず適切な target_date を渡してください。
- OpenAI API 呼び出しの失敗は基本的にフェイルセーフ（スコア 0.0 にフォールバックまたはスキップ）として継続する実装です。運用ポリシーにより厳格な失敗扱いが必要なら呼び出し側で検出してください。
- .env 自動ロードはデフォルトで有効ですが、CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

作者
- kabusys 開発チーム

--- 

（この CHANGELOG はコードベースの実装内容から自動的に推定して作成しています。ドキュメント化されていない動作や実環境での細かな挙動は実際のテスト・運用でご確認ください。）
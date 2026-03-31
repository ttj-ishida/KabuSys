CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョン番号はパッケージ src/kabusys/__init__.py の __version__ に基づきます。

Unreleased
----------

### 修正予定 / 既知の問題
- pipeline._get_max_date 関数の実装が途中で途切れており（return date.fro のような不完全な行が存在）、実行時に例外が発生する可能性があります。次回リリースで修正予定です。
- 一部のユーティリティはエラーハンドリングや境界条件の追加検討が必要（データ欠損・DB バージョン差異に関する互換性確認等）。詳細はコード内の TODO/コメントを参照してください。

0.1.0 - 2026-03-31
------------------

最初の公開リリース。以下の主要機能と設計方針を実装しています。

### 追加 (Added)
- 基本パッケージ構造を追加
  - パッケージエントリポイント: kabusys (version 0.1.0)
  - __all__ に data, strategy, execution, monitoring を公開

- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルートから自動ロード（優先順: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能（テスト用）。
  - export KEY=val、クォートやエスケープ、インラインコメントなどを考慮した .env パーサ実装。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境・ログレベル等をプロパティ経由で取得。
  - 必須環境変数未設定時は ValueError を送出。

- AI モジュール (kabusys.ai)
  - news_nlp: ニュース記事を OpenAI (gpt-4o-mini) にてセンチメント解析し ai_scores テーブルへ書き込むフローを実装。
    - タイムウィンドウ計算（JST 前日15:00～当日08:30）、銘柄ごとに記事を集約してバッチ送信（最大 20 銘柄/チャンク）、レスポンスバリデーション、スコアクリップ、部分更新（DELETE→INSERT）を行う。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ再試行を実装。
    - JSON Mode のレスポンスに対するパース＆余分な前後テキスト復元ロジックを実装。
  - regime_detector: ETF（1321）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して market_regime テーブルへ日次判定を保存。
    - MA 計算、マクロニュース抽出、OpenAI 呼び出し、スコア合成、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API エラー時は macro_sentiment を 0.0 としてフェイルセーフに継続。
  - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（モジュール内関数をパッチで mock できる設計）。

- データプラットフォーム (kabusys.data)
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等を提供。
    - market_calendar が未取得の場合は曜日ベース（土日除外）のフォールバックを採用。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（fetch + save のラッパー）を実装。バックフィル・健全性チェックを実装。
  - pipeline / etl: ETL の結果を表す ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - ETLResult は品質問題（quality.QualityIssue）やエラー一覧を収集し has_errors / has_quality_errors を提供。
    - pipeline モジュールに差分取得・保存・品質チェックの骨格を実装（J-Quants クライアント連携想定）。
  - jquants_client 等のクライアントと連携する想定の設計。

- リサーチ／因子計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算。
    - DuckDB 上の prices_daily / raw_financials を直接 SQL で処理する実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD による）を一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。3 銘柄未満は None を返す。
    - rank: 同順位は平均ランクとするランク付け実装（丸め処理を含む）。
    - factor_summary: count/mean/std/min/max/median を算出する集計ユーティリティ。
  - kabusys.research.__init__ で主要関数を再エクスポート。

### 変更 (Changed)
- 日時参照ポリシー: 多くのモジュールで datetime.today()/date.today() の直接参照を避け、必ず target_date を引数で渡す設計を採用（ルックアヘッドバイアス防止）。
- DuckDB 操作: 冪等性を重視した DELETE→INSERT の置換パターンおよび明示的な BEGIN/COMMIT/ROLLBACK を多用。
- OpenAI 呼び出し:
  - JSON Mode を用いた厳密な JSON 出力期待（レスポンスパースや余分テキスト復元ロジックを実装）。
  - 再試行／バックオフ戦略の統一（_MAX_RETRIES / _RETRY_BASE_SECONDS を使用）。

### 修正 (Fixed)
- （初版リリース）主要な機能は実装済みだが、pipeline._get_max_date の不完全な行など、少数の実装ミスが残っているため次回で修正予定。

### セキュリティ (Security)
- 特になし（秘密情報は環境変数で管理する設計、.env の取り扱いで OS 環境の保護を考慮）。

その他の注記
- エラーハンドリング方針:
  - AI/API 呼び出し失敗時はフェイルセーフで続行（多くの場合 0.0 や空結果へフォールバック）し、ログに警告を出力。
  - DB 書き込み失敗時は ROLLBACK を試み例外を再送出する設計。
- テスト/モック:
  - OpenAI 呼び出しはモジュール内の _call_openai_api をモックしやすいように分離してある（ユニットテストで差し替え可能）。
- 互換性:
  - DuckDB のバージョン差異（executemany の空リスト扱い等）に配慮した実装が含まれる。
- ドキュメント:
  - 各モジュールに設計方針・処理フローが詳細にコメント記載されており、参照可能。

今後の予定
- pipeline._get_max_date の修正およびパイプライン全体の統合テスト実施。
- エッジケースの追加テスト（欠損データ、DLL/DB バージョン差異、OpenAI レスポンスの異常形）を充実。
- 必要に応じてリファクタ（エラーメッセージの国際化、設定の型検証の強化等）。

--- 
（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリース履歴や日付はプロジェクトの運用方針に従って調整してください。）
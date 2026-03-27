CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

現在のリリース履歴
------------------

Unreleased
----------

- なし

0.1.0 - 2026-03-27
------------------

Added
- パッケージ初期公開（kabusys v0.1.0）
  - パッケージエントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"）
  - サブパッケージの公開: data, research, ai, execution, strategy, monitoring（__all__ を通じて公開）

- 環境設定管理モジュール（src/kabusys/config.py）
  - .env ファイルと環境変数を統合して読み込む自動ローダーを実装
    - プロジェクトルートは .git または pyproject.toml を基準に自動探索（CWD非依存）
    - 読み込み順序: OS環境変数（既存） > .env.local（上書き） > .env（未設定のみ）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）
    - .env 読み込み時に OS 環境変数を protected として上書きを保護
  - .env パーサーの拡張
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無しの行では '#' をインラインコメントとして扱うルール（直前が空白/タブの場合）
    - 無効行のスキップと読み込み失敗時の警告ログ
  - Settings クラスを提供（settings インスタンスで利用）
    - 必須設定取得用の _require を実装（未設定時は ValueError を発生）
    - J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level）等のプロパティ実装
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値以外は ValueError）
    - is_live / is_paper / is_dev の便利プロパティ

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメント分析（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に、銘柄ごとにニュースを集約し OpenAI（gpt-4o-mini）でセンチメントを算出
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ calc_news_window 実装
    - バッチ処理: 1 API コールあたり最大 20 銘柄（_BATCH_SIZE）
    - １銘柄あたりの記事は最大 10 件、テキストは最大 3000 文字にトリム
    - JSON Mode を使用し厳密な JSON レスポンスを期待、レスポンスの復元ロジックあり（前後テキスト混入への耐性）
    - リトライ/バックオフ戦略: 429/接続断/タイムアウト/5xx に対して指数バックオフでリトライ（上限回数定義）
    - レスポンス検証: results リスト・code の一致・数値スコア検証・±1.0 のクリップ
    - 部分成功に配慮した DB 書き込み（対象コードのみ DELETE → INSERT）で既存データ保護
    - API 呼び出しを差し替え可能（テスト用に _call_openai_api をモック可能）
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
    - マクロニュースは news_nlp.calc_news_window で抽出した期間のタイトルを用いて LLM（gpt-4o-mini）に投げる
    - LLM 呼び出しは JSON 出力を期待し、失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）
    - LLM へのリトライ/バックオフ・5xx 判定など堅牢なエラーハンドリングを実装
    - レジームスコアを -1.0〜1.0 にクリップし、閾値により 'bull'/'neutral'/'bear' ラベル付与
    - market_regime テーブルへ冪等的に（BEGIN / DELETE / INSERT / COMMIT）書き込み
    - 設計方針としてルックアヘッドバイアス対策（datetime.today() を参照しない、DB クエリは target_date 未満条件）

- Research モジュール（src/kabusys/research）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足は None）
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0/NULL の場合は None）
    - いずれの関数も DuckDB の prices_daily / raw_financials を参照し、本番発注 API にはアクセスしない設計
    - 営業日/スキャン幅のバッファを取り、週末や祝日を吸収する実装
  - feature_exploration.py
    - calc_forward_returns: target_date から各ホライズン（デフォルト [1,5,21] 営業日）までの将来リターンを計算
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算（有効レコードが 3 未満なら None）
    - rank: 同順位は平均ランクにするランク関数（float の丸めで ties 検出を安定化）
    - factor_summary: 指定カラムの count/mean/std/min/max/median を算出（None 値除外）
    - 標準ライブラリのみで実装（pandas 非依存）、DuckDB 接続を受ける

- Data モジュール（src/kabusys/data）
  - calendar_management.py
    - JPX カレンダー管理ユーティリティを実装
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar が未取得の場合は曜日ベースのフォールバック（平日を営業日扱い）
    - DB 登録値優先、未登録日は曜日フォールバックで一貫性を保つ（next/prev/get と整合）
    - 最大探索日数制限（_MAX_SEARCH_DAYS）を設けて無限ループ防止
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェックあり）
  - pipeline.py / etl.py
    - ETLResult データクラスを導入（ETL 実行結果の構造化）
      - 取得/保存カウント、品質問題リスト、エラーリスト、has_errors/has_quality_errors プロパティなど
      - to_dict により品質イシューをシリアライズ可能
    - ETL パイプライン設計（差分更新・保存・品質チェックの方針）を実装（jquants_client と quality を利用）
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、トレーディング日調整など

- パッケージ公開の小整理
  - ai.__init__ は score_news を再公開（news_nlp.score_news）
  - research.__init__ で主要関数を再エクスポート
  - data.etl は ETLResult を公開インターフェースとして再エクスポート

Changed
- (初回リリースのため該当なし)

Fixed
- (初回リリースのため該当なし)

Deprecated
- (初回リリースのため該当なし)

Removed
- (初回リリースのため該当なし)

Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を使用。キー未設定時は ValueError を送出して早期検出。

注記（設計上の重要ポイント）
- ルックアヘッドバイアス回避: 多くのコンポーネントで datetime.today()/date.today() を直接参照せず、明示的な target_date を受け取る設計としています。
- フェイルセーフ: AI/API の失敗時はスコアを 0.0 にフォールバックする、または該当コードだけスキップして他のデータを保護する等の堅牢化を行っています。
- DuckDB を主要な永続層として想定。executemany の空リストへの注意喚起（互換性対策）など実運用上の細かな配慮あり。
- テスト容易性: OpenAI 呼び出しを内部関数として抽象化し、unittest.mock.patch による差し替えを想定しています。

今後の予定（例）
- ファクター群の追加（PBR、配当利回り等）
- モデル運用向けの監視・アラート機能強化（monitoring パッケージ）
- kabuステーションとの発注ロジック（execution）と戦略実行基盤（strategy）の完成化

-----
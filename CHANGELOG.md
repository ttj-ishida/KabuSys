# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-27
初回リリース — 日本株自動売買 / データ分析基盤の基本機能を実装。

### 追加
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - export 可能なサブパッケージ一覧を __all__ で公開（data, research, ai, ...）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイル / 環境変数読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して自動読み込み（CWD に依存しない実装）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト等で利用）。
    - 読み込み時、OS の既存環境変数を protected として上書きを防止。
  - .env パーサーを実装（コメント、export プレフィックス、クォート文字とバックスラッシュエスケープ対応、インラインコメント処理など）。
  - 必須キー取得ユーティリティ _require（未設定時は ValueError を送出）。
  - Settings クラスでアプリケーション設定をプロパティとして公開（J-Quants / kabu / Slack / DB パス / 環境判定 / ログレベル等）。
    - KABUSYS_ENV, LOG_LEVEL の値検証（許容値以外は ValueError）。
    - duckdb / sqlite のデフォルトパスを設定。

- AI / ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを解析。
  - バッチ処理（1回につき最大 20 銘柄）とトークン肥大化対策（記事数・文字数上限）を導入。
  - API 呼び出しはリトライ（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実施。
  - レスポンスの厳密なバリデーション実装（JSON 抽出、results 配列チェック、コードの検証、スコアの数値検査、±1.0 クリップ）。
  - スコア書き込みは冪等性を確保（該当 date/code を DELETE → INSERT）。部分失敗時に既存スコアを保護する設計。
  - テスト容易性のため _call_openai_api をモジュール内で抽象化し、unittest.mock.patch により差し替え可能に。

- AI / 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（bull / neutral / bear）。
  - マクロキーワードによる raw_news フィルタリング、OpenAI による JSON 出力解析、フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
  - レジーム結果は market_regime テーブルに対して冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照せず、データ取得は target_date 未満の排他条件を利用。
  - OpenAI 呼び出しの個別実装によりモジュール結合を弱め、テスト時の差し替えが可能。

- データ処理 / カレンダー管理（kabusys.data.calendar_management）
  - JPX 市場カレンダー管理（market_calendar）と営業日判定ロジックを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
  - DB 登録値優先、未登録日は曜日ベースでフォールバック（週末を非営業日扱い）。
  - next/prev_trading_day は最大探索日数 (_MAX_SEARCH_DAYS) を設けて無限ループを防止。
  - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル、健全性チェックを含む）。

- データ処理 / ETL パイプライン（kabusys.data.pipeline, etl）
  - ETLResult データクラスを追加（ETL 実行結果を構造化して保持、品質問題やエラー情報を含む）。
  - 差分更新、backfill、品質チェック（quality モジュールへ委譲）に基づく ETL の設計方針を実装。
  - DuckDB を用いた最大日付取得やテーブル存在チェックなどのユーティリティを追加。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算機能を実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - calc_value: PER（EPS が利用可能な場合）と ROE を raw_financials と prices_daily を組み合わせて計算。
  - 特徴量探索ユーティリティ:
    - calc_forward_returns: 将来リターン（任意 horizon）を計算。
    - calc_ic: スピアマンランク相関（IC）を計算（欠損や等分散を考慮）。
    - factor_summary: 基本統計量（count, mean, std, min, max, median）を計算。
    - rank: 同順位を平均ランクで処理するランク化ユーティリティ。
  - zscore_normalize をデータユーティリティ層から再エクスポート。

### 変更（設計上の決定・注意点）
- API 呼び出しエラー時のフェイルセーフを明示（AI モジュールは API 失敗時でも例外を上げずスコアを 0.0 にして継続する設計が多い）。
- ルックアヘッドバイアス対策: 日付系処理はすべて外部から渡す target_date ベースで実装し、内部で date.today()/datetime.today() を参照しない。
- DuckDB の互換性を考慮した実装（executemany に空リストを渡さない等のワークアラウンド）。
- OpenAI レスポンスは JSON Mode を期待するが、前後テキスト混入を考慮して最外の {} を抽出して復元する処理を追加。
- ロギングを多用し、重要なフォールバックや例外発生時に警告/情報ログを出力するようにした。

### 修正（バグ修正 / 安全対策）
- .env 読み込みでのファイル読み取り失敗時に warnings.warn でユーザに通知するようハンドリング。
- DB 書き込みで例外発生時に ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告を出力する安全処理を追加。
- APIError の status_code 有無に依存しない安全な判定（getattr を利用）でリトライ判定を行うようにした。

### テストフレンドリー化
- OpenAI 呼び出しをモジュール内関数（_call_openai_api）に分離し、unittest.mock.patch 等で差し替えやすくしている箇所を複数実装（news_nlp, regime_detector）。

### 既知の制約 / 未実装
- PBR や配当利回りなどのバリューファクターは現バージョンでは未実装（calc_value に注記あり）。
- 外部依存を最小化する方針のため pandas 等の一般的な分析ライブラリには依存していない（標準ライブラリ + duckdb を利用）。
- AI モデルは gpt-4o-mini を想定している（将来的なモデル変更はパラメータ化の余地あり）。

---

今後の予定（例）
- エラー・品質チェック結果に基づくアラート/自動復旧フローの実装。
- 発注（execution）・モニタリング周りの実装強化（現在はモジュール構成のみ公開）。
- 一部計算を高速化するためのバルク DB 操作やキャッシュ機構の導入。

(この CHANGELOG はコードから推測して作成しています。実際の変更履歴とは差異がある場合があります。)
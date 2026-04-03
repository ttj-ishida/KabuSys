# CHANGELOG

すべての変更は Keep a Changelog の規約に従って記載しています。  
このファイルはリポジトリのコードベースから推測して生成された初期の変更履歴（リリースノート）です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-03
初回リリース

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys/__init__.py）。バージョン情報を `__version__ = "0.1.0"` として公開。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に登録。

- 設定管理
  - `kabusys.config` モジュールを追加
    - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートの探索は .git / pyproject.toml ベース）。
    - .env のパース実装（コメント行、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - OS 環境変数を保護する protected 上書き制御（.env.local を override=True で読み込む際に既存 OS 環境変数は保護）。
    - 設定アクセス用 `Settings` クラスを提供（例: `settings.jquants_refresh_token`、`settings.env`、`settings.log_level`、DB/監視関連のパスや閾値など）。
    - 環境変数の必須チェック `_require` を実装し、未設定時に明確な ValueError を送出。

- AI / 自然言語処理
  - `kabusys.ai.news_nlp`
    - ニュース記事を集約して OpenAI（gpt-4o-mini）へ投げ、銘柄ごとのセンチメントスコアを `ai_scores` テーブルへ保存する `score_news` を実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を `calc_news_window` で提供。
    - 1銘柄あたりの最大記事数・文字数トリム、最大バッチサイズ（20銘柄）などの防護措置を実装。
    - JSON Mode のレスポンス検証、部分失敗時に他銘柄スコアを保護する DELETE→INSERT の部分置換処理を実装。
    - RateLimit・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライロジックを実装。
    - テスト用フック: `_call_openai_api` をモック可能にして API 呼び出しを差し替え可能。

  - `kabusys.ai.regime_detector`
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する `score_regime` を実装。
    - マクロキーワードによる raw_news 抽出、OpenAI 呼び出しによる JSON パース、スコア合成と閾値判定、`market_regime` テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 のフォールバック（フェイルセーフ）を採用。
    - テスト用フック: `_call_openai_api` をモック可能。

- データプラットフォーム
  - `kabusys.data.calendar_management`
    - JPX カレンダー管理ロジック（market_calendar テーブルを利用）を実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。DB にデータがない場合は曜日ベースでフォールバック（週末を休場扱い）。
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装し、J-Quants API から差分取得して保存（バックフィル・健全性チェックを含む）。
    - 最大探索日数やバックフィル、ルックアヘッド等の定数を定義。

  - `kabusys.data.pipeline` / `kabusys.data.etl`
    - ETL パイプラインに関する実装骨格を追加。
    - `ETLResult` データクラスを公開（取得件数・保存件数・品質チェック結果・エラーログ等を保持）。
    - 差分更新、バックフィル、品質チェック（quality モジュール経由）の設計に準拠するインターフェースを提供。

- リサーチ / ファクター
  - `kabusys.research.factor_research`
    - モメンタム、ボラティリティ、バリュー関連ファクター計算関数を追加:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio
      - calc_value: per, roe（raw_financials の最新値を target_date 以前から取得）
    - DuckDB 上で SQL とウィンドウ関数を活用して計算。
    - データ不足時は None を返す安全設計。

  - `kabusys.research.feature_exploration`
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、factor_summary を実装。
    - Spearman（ランク）による IC 計算、統計要約、rank 関数は同順位の平均ランク対応。

- 公開インターフェースの整理
  - `kabusys.ai.__init__` と `kabusys.research.__init__` で主要関数を再エクスポート。
  - `kabusys.data.__init__` から pipeline の ETLResult を再エクスポート。

### 変更 (Changed)
- データ参照設計の一貫化
  - 全モジュール（AI / Research / Data / ETL）は datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）に統一。これによりルックアヘッドバイアスを防止。

- データベース操作の安全化
  - 各種書き込みは冪等性を考慮（DELETE→INSERT / ON CONFLICT 相当の扱い）し、トランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
  - DuckDB の executemany のバージョン差異（空リスト不可等）に配慮した実装を行い互換性を確保。

- OpenAI 統合
  - gpt-4o-mini を使用、JSON Mode を使った厳密な JSON 応答を期待するプロンプト設計とレスポンスバリデーションを導入。
  - レート制限や一時的 API エラーに対する再試行とログ出力を明確化。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - .env の解析において export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを正しく処理するように実装。
  - 不正な行やキー無し行を無視して読み込みの堅牢性を向上。

- エラー時のフォールバック
  - LLM 呼び出しや API パース失敗時に例外を直ちに投げず、0.0 や空スコアでフォールバックする（サービス継続性確保）。ログに警告を出力。

- DB ロールバックの堅牢化
  - 書き込み中に例外が発生した場合は ROLLBACK を試行し、ROLLBACK 自体の失敗も WARN ログに記録するように改善。

### セキュリティ (Security)
- 環境変数保護
  - `.env` 読み込み時に既存 OS 環境変数を protected として上書きから守る仕組みを導入（.env.local は override 可能だが OS 環境変数は保護）。
  - OpenAI API キーや各種トークンが未設定のまま呼び出すと明確なエラーを発生させる（ValueError）。

### 既知の制約 / 注意点 (Notes)
- OpenAI 連携は外部 API に依存するためネットワークやレート制限によりスコア取得が失敗する場合がある。実装は部分失敗を許容して全体の安定性を優先している（失敗時は部分的にスキップし、既存データを保護）。
- DuckDB のバージョン差異（executemany の空リスト扱い等）に注意しているため、環境によっては追加の検証が必要となる可能性がある。
- calendar_update_job や ETL 周りは外部 J-Quants クライアントに依存するため、実行時に正しい API 資格情報が必要。
- time / date の扱いはすべて timezone-naive の date / datetime を採用しており、UTC/JST の変換ロジックはモジュール内で明示的に扱われている（calc_news_window 等）。

---

今後予定（例）
- strategy / execution / monitoring の詳細実装・テストカバレッジの追加
- ドキュメント（Usage / API / データスキーマ）の拡充
- CI での DuckDB バージョン互換性テスト、OpenAI 呼び出しのモック化テスト強化

--------------------------------------------------------------------------------
（注）本 CHANGELOG は提供されたソースコードから推測して作成しています。実際のリリースノート作成時はコミット履歴・リリースノート等の一次情報を参照してください。
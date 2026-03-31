# Changelog

すべての注目すべき変更は、このファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

最新更新日: 2026-03-31

## [Unreleased]

## [0.1.0] - 2026-03-31
初期リリース。日本株自動売買システム「KabuSys」のコア機能群を提供します。

### 追加
- パッケージ構成と公開 API
  - パッケージメタ情報を追加: kabusys.__version__ = 0.1.0
  - パッケージ公開モジュール: data, strategy, execution, monitoring（__all__）

- 環境・設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）
  - .env パース実装の強化
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のエスケープ処理、インラインコメント処理を考慮
    - 無効行（空行やコメント行）をスキップ
  - _load_env_file による上書き / 保護キー（protected）機能を実装（OS 環境変数保護）
  - Settings クラスで主要設定をプロパティとして公開
    - J-Quants / kabuステーション / Slack / DB パス等を取得
    - env と log_level の検証（許容値チェック）
    - Path 型での duckdb/sqlite パス展開
    - is_live / is_paper / is_dev のユーティリティ

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約し、銘柄ごとのセンチメントを OpenAI (gpt-4o-mini) に依頼
    - バッチ処理: 最大 20 銘柄／API コール、1銘柄あたり最大 10 記事・3000 文字でトリム
    - JSON mode を利用し厳格な JSON 出力を期待。レスポンス検証・復元ロジックあり（余分な前後テキストの {} 抽出等）
    - 429/ネットワーク断/タイムアウト/5xx に対する指数的バックオフリトライ
    - スコアを ±1.0 にクリップし、取得成功銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT、部分失敗時の保護）
    - テスト容易性: api_key 注入可能、_call_openai_api のパッチによる差し替え想定
    - タイムウィンドウ定義（JST ベース）と UTC 変換ユーティリティ (calc_news_window)
    - DuckDB 0.10 互換性対策（executemany に空リストを渡さない）
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定
    - ma200_ratio の計算（target_date 未満データのみを使用しルックアヘッド防止）
    - マクロニュースはニュースタイトルをキーワードで抽出（複数キーワード定義）
    - OpenAI 呼び出しは独立実装、失敗時は macro_sentiment=0.0 としてフェイルセーフ
    - リトライ・バックオフと 5xx 判定・ログ出力を実装
    - 結果は market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）

- データ処理 (kabusys.data)
  - ETL パイプラインインターフェース
    - ETLResult データクラス（ETL 実行結果の集約とシリアライズ用 to_dict）を提供（kabusys.data.pipeline）
    - kabusys.data.etl で ETLResult を再エクスポート
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を使った営業日判定ユーティリティ群を提供
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB データ優先、未登録日は曜日ベースでのフォールバック（DB がまばらな状況でも一貫性を維持）
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックあり
    - 最大探索日数やバックフィル日数等の安全装置を実装（無限ループ防止・将来日付異常検出）
  - ETL 実装ガイドラインに沿ったユーティリティ（差分更新、品質チェック連携、バックフィル等）

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum: 1M/3M/6M のリターン、200 日移動平均乖離（ma200_dev）
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、平均売買代金、出来高比率
    - Value: PER（EPS が有効な場合）、ROE（raw_financials から最新財務データを取得）
    - DuckDB 上で SQL を活用した実装、データ不足時は None を返す
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Information Coefficient、Spearman の ρ）計算（rank を内部実装）
    - factor_summary: カラムごとの基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクを返す実装（丸めで ties の安定化）

### 改良 / 設計方針
- ルックアヘッドバイアス防止を徹底
  - いずれのモジュールでも datetime.today()/date.today() をスコープ内で直接参照せず、外部から target_date を与える設計
  - prices_daily などのクエリは target_date 未満（排他）または明示的に範囲制限して未来データを使用しない
- テスト容易性を意識した実装
  - OpenAI 呼び出しのラッパー関数を用意しテストで差し替え可能
  - api_key を引数注入できる API を提供
- フェイルセーフとログ重視
  - LLM / API エラー時は例外で破棄せずフェイルセーフ値（例: 0.0）で継続し、WARNING/INFO/DEBUG で詳細ログを出力
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）を使用し、失敗時はロールバックして上位へ伝播

### 既知の仕様・制約
- OpenAI モデルは gpt-4o-mini を前提にプロンプト設計（JSON mode を期待）
- DuckDB のバージョン互換性を考慮した実装（executemany の空リスト回避等）
- 一部の高度なファイナンシャル指標（PBR・配当利回りなど）は未実装（将来の拡張対象）
- calendar_update_job や ETL 周りは J-Quants クライアント実装（kabusys.data.jquants_client）との連携を前提

### 変更なし / 破壊的変更なし
- 初期リリースのため、後方互換性に関する制約は現時点で無し（将来的に API 変更の可能性あり）

---

今後のリリースでは以下を予定しています（候補）:
- 戦略定義・実行モジュール（strategy / execution）の充実
- 追加ファクター・財務指標の実装（PBR、配当利回り等）
- モデル監視・アラート機能（monitoring）の実装強化
- テストカバレッジの拡充と CI 統合

もし追加で詳細な変更点や、各モジュールの公開 API ドキュメント風の記載を希望される場合は教えてください。
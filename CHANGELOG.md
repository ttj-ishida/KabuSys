# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31
初期リリース。日本株自動売買支援ライブラリ "kabusys" の最初の機能群を追加。

### 追加 (Added)
- パッケージ全体
  - パッケージ識別子を src/kabusys/__init__.py に追加（__version__ = "0.1.0"、__all__ 定義）。
  - モジュール構成: data, research, ai, (strategy, execution, monitoring を公開対象に含むが実装は分割)。

- 設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルと OS 環境変数から設定を自動読込する仕組みを実装。
  - プロジェクトルート検出（.git または pyproject.toml ベース）により CWD に依存しない自動ロード。
  - .env パーサを実装（export 形式、クォート、エスケープ、インラインコメント対応）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）などのプロパティを取得・検証（未設定時は例外）。
  - LOG_LEVEL / KABUSYS_ENV の妥当性チェック実装。

- データプラットフォーム (src/kabusys/data/)
  - calendar_management モジュール
    - market_calendar テーブルを用いた営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータが無い場合は曜日ベース（土日除外）でフォールバック。
    - カレンダー夜間バッチ更新 job (calendar_update_job): J-Quants から差分取得し冪等保存。バックフィル・健全性チェックを実装。
  - pipeline / etl
    - ETLResult データクラスを実装（ETL 実行結果・品質問題・エラーを集約）。
    - ETL パイプラインの設計骨格（差分取得、保存、品質チェック、backfill の方針）を実装（jquants_client, quality モジュールとの連携想定）。
  - etl モジュールから ETLResult を公開。

- AI モジュール (src/kabusys/ai/)
  - news_nlp モジュール
    - raw_news / news_symbols を元にニュースを銘柄別に集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄別センチメントを評価（score_news）。
    - バッチ処理（最大 20 銘柄/回）、1銘柄あたり最大記事数と文字数制限、レスポンス検証、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。失敗はフェイルセーフでスキップ（例外を上げず継続）。
    - レスポンスの JSON パース耐性（前後余計なテキストから {} を抽出するロジック）を実装。
    - ai_scores テーブルへの冪等的な書き込み（DELETE → INSERT、部分失敗時に既存スコア保護）。
  - regime_detector モジュール
    - ETF 1321（日経225連動）200日移動平均乖離とマクロニュース（LLM）を組み合わせ市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む（score_regime）。
    - ma200_ratio 計算（target_date 未満のデータのみ使用、データ不足時は中立値 1.0 を返す）。
    - マクロ記事抽出（キーワードベース）と LLM による macro_sentiment 評価（JSON レスポンスパース、リトライ/フェイルセーフ）。
    - レジームスコア合成（MA 重み 70%、マクロ 30%）と冪等 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - ai パッケージの公開インターフェース（score_news, score_regime を想定でエクスポート）。

- リサーチ（因子計算） (src/kabusys/research/)
  - factor_research モジュール
    - モメンタムファクター（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性指標（20日平均売買代金、出来高比率）、バリューファクター（PER, ROE）を DuckDB 上の SQL で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の挙動（該当値を None）や範囲スキャン戦略を設計。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（Spearman のランク相関）計算（calc_ic）、ランク変換、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB クエリで実装。
  - research パッケージの public API を整備（各種計算関数を __all__ で再エクスポート）。

### 変更 (Changed)
- なし（初回リリースのため該当なし）。

### 修正 (Fixed)
- なし（初回リリースのため該当なし）。

### 既知の制限・設計上の注意 (Notes)
- 多くのモジュールで datetime.today() / date.today() を直接参照しない設計（ルックアヘッドバイアス回避）。代わりに target_date を明示的に受け取る API を採用している。
- OpenAI API 呼び出し部分は明示的にリトライとフェイルセーフを実装しており、API 失敗時にはスキップして処理継続することが多い（運用者はログを監視すること）。
- 一部機能は将来的拡張の余地あり（例: Value ファクターでの PBR・配当利回りは未実装）。
- DuckDB バインディングの互換性（executemany の空リスト禁止など）に配慮した実装を行っている。
- calendar_update_job 等は jquants_client の存在を前提とする（外部 API クライアントとの連携が必要）。

### 互換性 (Compatibility)
- 破壊的変更はなし（初回リリース）。

---

（注）この CHANGELOG はソースコードの内容から推測して作成した初期リリースログです。実際のリリースノート作成時には、リリース日・貢献者情報・外部依存の正確なバージョンなどを補完してください。
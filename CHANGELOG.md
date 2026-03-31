# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョン: 0.1.0

<!-- 年-月-日 はリリース日を記載しています -->
## [Unreleased]

今後の予定・メモ（実装済みだが次バージョンで注記する可能性がある項目、もしくは既知の改善点）
- OpenAI 呼び出しのモデルや JSON Mode の振る舞いに対する追加検証／エラーハンドリングの強化
- news_nlp / regime_detector のテストカバレッジ拡大（外部 API モックの標準化）
- strategy / execution / monitoring パッケージの公開 API の整備（__all__ に含まれているが実装状況を整理）
- DuckDB バインディング周りの互換性確認（バージョン依存の挙動に対する CI テスト追加）

---

## [0.1.0] - 2026-03-31

初回公開リリース。パッケージ名: kabusys。日本株自動売買プラットフォームのデータ処理・研究・AI補助機能群を提供。

### 追加 (Added)
- パッケージ基盤
  - src/kabusys/__init__.py にてバージョンを定義（__version__ = "0.1.0"）し、主要サブパッケージを公開（data, strategy, execution, monitoring を __all__ に含む）。
- 環境設定管理
  - src/kabusys/config.py
    - .env/.env.local をプロジェクトルート（.git か pyproject.toml）から自動ロードする仕組みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - export KEY=val 形式やクォート、インラインコメントなどに対応した .env パーサーを実装。
    - OS 環境変数を保護するための protected 上書き制御（.env.local は override=True）。
    - 設定取得用の Settings クラスを追加。J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）等をプロパティで提供。
    - 必須環境変数未設定時に ValueError を送出する _require ユーティリティを実装。
- AI 関連
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_score）を算出、ai_scores テーブルへ書き込む機能を実装。
    - チャンク処理（最大 20 銘柄/回）、トークン肥大対策（記事数・文字数制限）、リトライ（429/タイムアウト/5xx の指数バックオフ）を含む堅牢な実装。
    - レスポンスのバリデーション、スコアの ±1.0 クリップ、部分的書き換え（DELETE→INSERT）による冪等性設計。
    - テスト向けに _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みする機能を実装。
    - マクロニュース抽出、OpenAI 呼び出し（モデル gpt-4o-mini）、リトライロジック、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止設計（datetime.today() を参照しない、DB クエリは target_date 未満の排他条件）。
- データ基盤
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基礎（差分取得、保存、品質チェックを想定）と ETLResult データクラスを実装。ETL の取得数・保存数・品質問題・エラー一覧を集約可能。
    - ETLResult.to_dict による監査ログ用の辞書出力。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - calendar_update_job による J-Quants からの夜間差分取得と冪等保存（バックフィル・健全性チェックを含む）を実装。
    - DB にデータが無い場合は曜日ベースのフォールバック（週末を非営業日）を使用する設計。
- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - ファクター計算（モメンタム、ボラティリティ、バリュー）を実装: mom_1m/mom_3m/mom_6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe 等。
    - DuckDB SQL を主体にして prices_daily / raw_financials を参照する設計。結果を (date, code) 辞書リストで返却。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB で完結する実装。
  - src/kabusys/research/__init__.py で主要関数を公開（zscore_normalize は外部 data.stats から）。
- 依存・運用上の配慮
  - OpenAI API の呼び出しには OPENAI_API_KEY が必要。api_key 引数で上書き可能。
  - DuckDB を想定した SQL 実行・トランザクション（BEGIN/COMMIT/ROLLBACK）処理を使用。部分失敗時に既存データを保護する設計が随所にある。
  - ログ出力（logger）を多用し、失敗時は警告/情報を残して継続するフェイルセーフ設計。

### 変更 (Changed)
- 初回リリースのため、変更履歴はなし。

### 修正 (Fixed)
- 初回リリースのため、修正履歴はなし。

### 破壊的変更 (Removed / Deprecated)
- なし（初回リリース）。

### 既知の制限・注意点
- OpenAI 呼び出しは外部サービスに依存するため、API 使用料・レート制限に注意が必要。エラー時はスコアを落ち着かせる（0.0 にフォールバック）実装になっているが、運用時はリトライや監視の調整を推奨。
- DuckDB のバージョンによっては executemany の挙動やリスト型バインドの互換性が問題となるため、個別 DELETE を使用する等の互換性対策を講じている。環境によっては追加検証が必要。
- .env パーサーは一般的なフォーマットに対応しているが、稀なケースのパース差異がある可能性がありテスト推奨。
- strategy / execution / monitoring の公開を __all__ に含めているが、今回のリリースでの実装状況により API の安定化が今後の課題となる可能性あり。

---

作業メモ:
- この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のコミット履歴やリリースノートに応じて適宜更新してください。
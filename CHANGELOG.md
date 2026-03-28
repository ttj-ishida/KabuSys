# CHANGELOG

すべての重要な変更点は Keep a Changelog のフォーマットに従って記載しています。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システムのコアライブラリを追加。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py に __version__ を定義）
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution 等の想定（__all__ に data, strategy, execution, monitoring を設定）

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env/.env.local の優先順・上書き制御（OS環境変数保護、.env.local は override）を実装。
  - 複雑な .env 行パースに対応（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い）。
  - 必須環境変数取得（_require）と Settings クラスを提供（J-Quants / kabu-API / Slack / DB パス / 実行環境 / ログレベルなどのプロパティ）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値以外は ValueError）。

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメント分析（news_nlp.score_news）
    - raw_news / news_symbols を集約して銘柄単位に記事をまとめ、OpenAI（gpt-4o-mini）を JSON Mode で呼び出して銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄/chunk）、記事数・文字数制限（1銘柄当たり最大記事数・文字数）によるトークン肥大化対策。
    - エラー時はフェイルセーフでスキップし続行（429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ）。
    - レスポンスの厳格なバリデーション（JSON パース復元ロジック、results 配列・各要素の code/score 検証、スコアのクリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。テスト容易性のため _call_openai_api をモック可能。
    - タイムウィンドウは JST 基準で定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して DB と照合）。

  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）判定。
    - マクロセンチメントは指定キーワードでフィルタしたニュースタイトルを LLM に投げて評価。記事がない場合は LLM 呼び出しを行わず 0.0 を使用。
    - API 呼び出しは最大リトライ、500 系判定で再試行。失敗時はマクロセンチメントを 0.0 にフォールバック（フェイルセーフ）。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、例外発生時に ROLLBACK を試行）。

- データプラットフォーム（src/kabusys/data）
  - ニュース・ETL・カレンダー関連の基盤実装
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB が不完全な場合の曜日ベースフォールバック（週末除外）を実装。最大探索日数上限で無限ループを防止。
    - 夜間バッチ更新 job（calendar_update_job）を実装し、J-Quants クライアントを通じて差分取得・冪等保存を行う。バックフィルと健全性チェックを実装。
  - ETL / pipeline
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分更新、バックフィル、品質チェックの統合フローを想定したユーティリティを実装（_get_max_date 等のヘルパー含む）。
    - ETL 実行結果は品質問題とエラー概要を集約可能。

- リサーチモジュール（src/kabusys/research）
  - factor_research（calc_momentum, calc_value, calc_volatility）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、バリュー（PER/ROE）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比）を DuckDB 内で SQL により計算。
    - データ不足時の None 処理、営業日スキャンのバッファ設定、結果は (date, code) をキーとする dict のリストで返却。
  - feature_exploration（calc_forward_returns, calc_ic, factor_summary, rank）
    - 将来リターン（任意ホライズン）計算、Spearman ランク相関（IC）の計算、ファクター統計サマリー、ランク関数を実装。
    - pandas 等外部依存なし、標準ライブラリ + DuckDB での実装。

### 設計上の注意点 / 挙動
- ルックアヘッドバイアス回避
  - いずれの AI / リサーチ処理も内部で datetime.today()/date.today() を参照せず、明示的な target_date を受け取る設計。
  - DB クエリは target_date 未満・未満区間等でルックアヘッドを避ける条件を使用。

- フェイルセーフ
  - 外部 API（OpenAI / J-Quants 等）のエラー時は、安全にフォールバック（例: macro_sentiment = 0.0）して処理継続することを優先。
  - DuckDB への複雑な書き込みはトランザクションで囲み、失敗時は ROLLBACK を試行。

- テスト容易性
  - OpenAI 呼び出し部分は内部で _call_openai_api を使うため、unittest.mock.patch による差し替えが可能。

### 既知の制限
- 一部機能は外部クライアント実装に依存（例: kabusys.data.jquants_client の実装を前提としている）。
- GUI や実際の売買執行ロジック（execution / strategy / monitoring）については公開された関数やインターフェースの骨子はあるが、本リリースではデータ収集・スコアリング・リサーチ側に重点を置いている。

### セキュリティ
- API キーは引数経由または環境変数（OPENAI_API_KEY など）で提供する設計。キーの安全な管理（環境変数・Vault 等）を推奨。

---

今後のリリースでは、発注/実行関連モジュールの具体的な実装、テストカバレッジ強化、運用向け監視・アラート機能の追加を予定しています。
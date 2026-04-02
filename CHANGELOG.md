# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  

※コードベースの内容から推測して作成しています。実際の変更履歴と差異がある可能性があります。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-02
初回公開リリース。本バージョンで提供される主な機能と実装上の要点は以下の通りです。

### 追加 (Added)
- 基本パッケージ
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を設定。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に追加。

- 設定管理 (src/kabusys/config.py)
  - .env/.env.local の自動ロード機能を実装（プロジェクトルート検出は .git または pyproject.toml に依存）。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理などに対応。
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB /監視 / システム設定を環境変数から安全に取得（必須チェックと検証含む）。
  - 環境値の検証: KABUSYS_ENV と LOG_LEVEL の有効値チェックを実装。

- ニュースNLP & レジーム検出 (src/kabusys/ai)
  - news_nlp モジュール: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込み。
    - バッチ処理、チャンクサイズ制御（最大20銘柄）、1銘柄あたりの記事数・文字数制限、JSON mode による厳密なレスポンス期待。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列・code/score 検証、スコアのクリップ）。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）。
    - フェイルセーフ設計: APIエラー時は該当チャンクをスキップして処理継続。
  - regime_detector モジュール: ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ冪等書き込み。
    - MA 計算は target_date 未満のみを使用してルックアヘッドを防止。
    - マクロニュース抽出（キーワードリスト）、LLM 呼び出しの再試行・フォールバック（失敗時は macro_sentiment = 0.0）。
    - OpenAI 呼び出しは内部で独立実装（モジュール間でプライベート関数を共有しない設計）。

- データ基盤 (src/kabusys/data)
  - calendar_management モジュール:
    - market_calendar に基づく営業日判定とユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データ優先、未登録日は曜日ベースでのフォールバック。探索は最大範囲制限（保護）。
    - JPX カレンダー差分取得と夜間バッチ更新（calendar_update_job）を実装。バックフィル日数・健全性チェックを備える。
  - pipeline / etl:
    - ETLResult データクラスを公開（etl モジュールから再エクスポート）。ETL 実行結果・品質問題・エラーを集約可能。
    - ETL の設計方針に従った定数やユーティリティ関数を実装（差分取得、バックフィル、品質チェックのための土台）。

- リサーチ (src/kabusys/research)
  - factor_research モジュール:
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20日）、流動性指標（20日平均売買代金、出来高比）等の定量ファクター計算を実装。
    - DuckDB を用いた SQL ベースの計算（ルックバック範囲の確保、データ不足時の None 処理など）。
  - feature_exploration モジュール:
    - 将来リターン計算（calc_forward_returns、ホライズンはデフォルト [1,5,21]、引数検証あり）。
    - IC（Information Coefficient）計算（スピアマンランク相関）、ランク化ユーティリティ（ties は平均ランク）、ファクター統計サマリー関数を実装。
  - 研究用ユーティリティの公開（zscore_normalize は data.stats から利用）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数の必須チェック（_require）により、トークンやパスワードが未設定のまま動作するリスクを低減。
- .env 読み込み時に既存 OS 環境変数を保護する protected オプションを導入。

### 実装上の注意（設計ポリシーと制約）
- すべてのバッチ処理・スコアリング関数は datetime.today() / date.today() を直接参照せず、target_date 引数を基準にしてルックアヘッドバイアスを防止する設計。
- OpenAI 呼び出しは JSON Mode を期待しつつ、実運用での不確実性に備えて厳格なパース/検証とフォールバックを行う。
- DuckDB の executemany の挙動（空リスト不可など）や日付型の扱い（date オブジェクトへの変換）を考慮した実装。
- ETL / カレンダ更新は idempotent（冪等）に設計。DB への書き込みは DELETE→INSERT や ON CONFLICT 相当の扱いで部分失敗時のデータ保護を意識。

---

今後の予定（推測）
- execution / monitoring 周りの実装公開（発注・実行エンジン、プロセス監視・アラート）。
- 追加の品質チェック、ユニットテスト、ドキュメント整備、例外ハンドリング強化。

もし実際のコミット履歴やリリース日がある場合は、その情報を提供いただければ CHANGELOG を実際の履歴に合わせて更新します。
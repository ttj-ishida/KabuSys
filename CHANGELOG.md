# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースポリシー: 主要な機能追加は "Added"、API 変更は "Changed"、不具合修正は "Fixed" に記載します。

---

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買・データ基盤・リサーチのためのコアモジュール群を実装しました。主な追加点と設計方針は以下の通りです。

### Added
- パッケージ基盤
  - パッケージバージョン設定とエクスポート: `kabusys.__version__ = "0.1.0"`、主要サブパッケージを __all__ で公開。

- 環境設定管理 (`kabusys.config`)
  - .env/.env.local の自動読み込み機能（OS 環境変数より低優先、.env.local は上書き）を実装。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索するため、CWD 非依存で動作。
  - .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - OS 環境変数を保護するための protected keys 機構。
  - 必須環境変数取得時の検証ヘルパー `_require` と設定アクセスラッパー `Settings` を提供。J-Quants / kabuAPI / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベル検証を含む。

- AI（自然言語処理）モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - ニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を提供。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、最大記事数・文字数でトリム。
    - OpenAI（gpt-4o-mini）の JSON mode を使い、最大 20 銘柄/チャンクでバッチ送信。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスバリデーション（JSON 抽出、results 配列チェック、コード整合性、スコア数値化）を行い ±1.0 にクリップ。
    - スコア取得済みコードのみ ai_scores テーブルに対して DELETE → INSERT（冪等性・部分失敗保護）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（ユニットテストでの patch を想定）。

  - 市場レジーム判定 (`ai.regime_detector.score_regime`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を推定。
    - マクロキーワードで raw_news をフィルタリングし、LLM（gpt-4o-mini）へ投げる。無記事時は LLM 呼び出しを行わず macro_sentiment=0.0。
    - API エラー時はフェイルセーフとして macro_sentiment=0.0 を使用し処理継続。
    - レジームスコアはクリップしてラベル化し、market_regime テーブルへ冪等的に（BEGIN/DELETE/INSERT/COMMIT）書き込み。
    - OpenAI クライアント呼び出しとリトライロジックを分離・実装。

- データ / ETL / カレンダー (`kabusys.data`)
  - カレンダー管理 (`data.calendar_management`)
    - JPX カレンダー管理用のユーティリティ群（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - market_calendar が未取得の場合は曜日ベース（土日非営業日）でフォールバックする一貫した挙動を採用。
    - カレンダー夜間更新ジョブ `calendar_update_job`：J-Quants から差分取得 → 保存（ON CONFLICT DO UPDATE）・バックフィル（直近 N 日）・健全性チェックを実装。
    - 最大探索日数や健全性チェックを導入し無限ループや極端なデータを防止。

  - ETL パイプライン (`data.pipeline` / `data.etl`)
    - ETL 実行結果用データクラス `ETLResult` を提供（取得件数、保存件数、品質チェック問題リスト、エラー一覧等を収集・シリアライズ可能）。
    - 差分更新・バックフィル・品質チェックを想定した設計方針を記載（実装の土台を提供）。
    - DuckDB に対する存在確認や最大日付取得などのユーティリティを実装。

  - jquants_client 経由での保存/取得フック（jquants_client は外部モジュールとして利用想定）。

- 研究用ユーティリティ (`kabusys.research`)
  - ファクター計算 (`research.factor_research`)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を DuckDB の SQL と Python で計算する関数を実装。prices_daily / raw_financials のみを参照。
    - データ不足時は None を返す等、堅牢な取り扱い。
  - 特徴量探索 (`research.feature_exploration`)
    - 将来リターン計算（任意ホライズン）、IC（Spearman のランク相関）、ランク換算ユーティリティ、ファクター統計サマリーを実装。
    - pandas に依存しない純 Python 実装。
  - zscore 正規化ユーティリティの再公開（kabusys.data.stats の利用を想定）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの扱いは引数優先、未指定時は環境変数 `OPENAI_API_KEY` を参照。未設定時は明示的に ValueError を送出して誤った黙殺を防止。
- .env 読み込みは標準 UTF-8 とし、読み込み失敗時は警告を出し処理継続。

### Design / Reliability notes
- ルックアヘッドバイアス防止: ほとんどの処理で datetime.today() / date.today() を直接参照せず、呼び出し側が target_date を渡す設計。
- DuckDB に対してはトランザクション制御（BEGIN/COMMIT/ROLLBACK）を使用し、部分失敗時のロールバックやログ出力を整備。
- API 呼び出しはリトライ（指数バックオフ）を実装。致命的エラーを避けるため、API 失敗時はゼロやスキップで継続するフェイルセーフ動作を採用。
- テスト可能性: OpenAI 呼び出し部分をモジュール内で分離しているためユニットテストで差し替えやスタブが可能。

### Known limitations / TODO
- PBR や配当利回りなど一部バリューファクターは未実装（calc_value の注記参照）。
- jquants_client の実体は外部依存のため、実行には該当クライアントの実装が必要。
- DuckDB の executemany に空リストを渡せない制約へのワークアラウンド実装を行っている（互換性のため）。将来 DuckDB のバージョン差異に合わせた検証が必要。

---

今後のリリースでは、以下を予定しています（例）:
- AI モデル評価・比較やプロンプト最適化の改善
- ETL の自動スケジューリング・モニタリング機能
- 追加ファクター（PBR、配当利回り等）とリスク調整ロジック
- 単体テストの充実と CI ワークフローの追加

--- 

（注）この CHANGELOG はコード内のコメント・実装から推測して作成しています。実際のリリースノートを作成する際は、運用上の変更点・マイグレーション手順・既知の動作差異などを適宜追記してください。
# Changelog

すべての注目すべき変更点をここに記載します。  
形式は「Keep a Changelog」に準拠します。  

※以下の履歴はリポジトリ内のソースコードから機能追加・設計方針・振る舞いを推測して作成しています。

## [Unreleased]

### Added
- なし（現行バージョンは 0.1.0 を参照してください）。

---

## [0.1.0] - 2026-03-29

初期リリース。日本株自動売買システム「KabuSys」のコアライブラリを実装しました。主な追加点は以下の通りです。

### Added — 基本パッケージ
- パッケージのエントリポイント `kabusys` を追加。公開 API として `data`, `strategy`, `execution`, `monitoring` を想定してエクスポート。
- バージョン情報を `__version__ = "0.1.0"` として定義。

### Added — 設定 / 環境変数管理 (kabusys.config)
- .env / .env.local ファイル自動読み込み機能を実装（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。
- 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
- .env パーサーの強化:
  - `export KEY=val` 形式に対応。
  - シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを実装。
  - 無効行（空行、コメント行、Key=値でない行）はスキップ。
- ファイル読み込み時に既存OS環境変数を保護する仕組み（protected set）を追加。
- `Settings` クラスを追加。環境変数経由でアプリ設定を取得するプロパティを提供：
  - J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite） / 実行環境（development/paper_trading/live） / ログレベル。
- 必須環境変数未設定時は `_require` で `ValueError` を送出し明示的に通知。

### Added — AI モジュール (kabusys.ai)
- ニュースNLP スコアリング（kabusys.ai.news_nlp）:
  - raw_news / news_symbols からニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントを算出。
  - タイムウィンドウ（JST 前日15:00 ～ 当日08:30）を計算する `calc_news_window` を提供。
  - バッチ処理（最大 20 銘柄）・記事数/文字数トリム・スコアクリップ（±1.0）・レスポンス検証を実装。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ再試行を実装。
  - レスポンスのパース失敗やAPI失敗は例外を投げずフェイルセーフでスキップ（ログ出力）。
  - 成功スコアは `ai_scores` テーブルへ冪等（DELETE → INSERT）で書き込み。
  - テスト容易性のため OpenAI 呼び出し部分は内部でラップしており `unittest.mock.patch` で差し替え可能。
- 市場レジーム判定（kabusys.ai.regime_detector）:
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
  - マクロキーワードで raw_news をフィルタし、最大 20 件を LLM に投げて macro_sentiment を算出。
  - LLM 呼び出しのリトライ、5xx 判定、失敗時フォールバック（macro_sentiment=0.0）を実装。
  - 結果は `market_regime` テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
  - ルックアヘッドバイアス防止のため、内部で現在日時を参照せず、target_date 未満のデータのみを使用する設計。

### Added — データプラットフォーム (kabusys.data)
- マーケットカレンダー管理（kabusys.data.calendar_management）:
  - `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を実装。
  - DB（market_calendar）からの値を優先し、登録がない日は曜日（土日）ベースでフォールバック。
  - 最大探索日数制限（_MAX_SEARCH_DAYS）や健全性チェックを導入し無限ループや異常データを防止。
  - 夜間更新ジョブ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得 → 保存、バックフィル _BACKFILL_DAYS を含む）。
- ETL / Pipeline（kabusys.data.pipeline, kabusys.data.etl）:
  - ETL 実行結果を保持する `ETLResult` データクラスを追加（品質チェック結果やエラー一覧を含む）。
  - 差分取得・バックフィル・品質チェックを想定したユーティリティを実装（テーブル存在確認、最大日付取得等）。
  - jquants_client 経由の保存処理（idempotent な保存）を想定した設計。
- jquants_client や quality との連携ポイントを想定した構成。

### Added — リサーチ / ファクター計算 (kabusys.research)
- ファクター計算（kabusys.research.factor_research）:
  - モメンタム（約1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR, 相対ATR）、流動性（20日平均売買代金、出来高比）、バリュー（PER, ROE）を計算する関数を実装。
  - DuckDB のウィンドウ関数を活用し、データ不足時は None を返す等の堅牢な設計。
- 特徴量探索（kabusys.research.feature_exploration）:
  - 将来リターン計算（任意ホライズンの fwd_*）、IC（Spearman の ρ）計算、rank ユーティリティ、ファクター統計サマリーを実装。
  - pandas 等に依存せず、純標準ライブラリと DuckDB の SQL で実装。

### Added — 共通設計方針 / 実装上の注意点
- ルックアヘッドバイアス防止: 多くの関数が内部で datetime.today()/date.today() を参照せず、外部から target_date を受け取る設計。
- DB 書き込みは可能な限り冪等に設計（DELETE → INSERT のパターン、BEGIN/COMMIT/ROLLBACK）。
- OpenAI 呼び出しは JSON Mode（response_format 指定）を利用し、レスポンス検証を厳密に行う。
- フェイルセーフ: API やデータ不足、パース失敗時は例外を大きく投げずログ出力のうえ安全なデフォルトで継続する設計（運用継続優先）。
- テストしやすさの配慮: OpenAI 呼び出しなど外部依存を内部でラップし、テスト時に差し替え可能。

### Dependencies / Runtime
- DuckDB をデータプラットフォームの主要 DB として利用。
- OpenAI Python クライアント（chat completions）を利用して LLM 呼び出しを行う（モデル: gpt-4o-mini を指定）。
- 環境変数により J-Quants / Kabu / Slack の認証情報を受け取る設計。

### Documentation / Logging
- 各モジュールに詳細な docstring と設計方針を追加し、ログメッセージ（logger）で実行状況を出力するよう実装。

---

過去の変更や将来のリリースをこのファイルに追加してください。重要な変更（API 破壊的変更、セキュリティ修正、重大バグ修正）は目立つように別項目で記載することを推奨します。
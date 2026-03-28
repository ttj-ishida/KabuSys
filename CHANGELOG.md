# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠しています。  

現在のリリース方針:
- バージョニングは SemVer を想定しています。
- 本CHANGELOGはコードベースから推測して作成しています（実装状況に基づく初版リリース記録）。

## [Unreleased]
- 今後の変更・改善をここに記載します。

## [0.1.0] - 2026-03-28
初期リリース（推定）。以下の主要機能とモジュールを追加しました。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのバージョン情報を追加（__version__ = "0.1.0"）。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env / .env.local の読み込み順序をサポート（OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化をサポート（テスト向け）。
  - export KEY=val 形式やクォート/エスケープ、行内コメント取り扱いに対応した .env パーサを実装。
  - Settings クラスを追加し、J-Quants / kabu API / Slack / DB パス / システム設定等のプロパティを提供（必須環境変数未設定時は ValueError を送出）。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約して銘柄毎にニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ保存。
    - バッチ処理（最大 20 銘柄/回）、1銘柄あたりの最大記事数・文字数トリム、JSON Mode を使用したレスポンス検証を実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - レスポンス検証で results キー、型、既知コードフィルタ、スコア数値チェック等を行い、不正レスポンスはスキップしてフォールバック。
    - テスト容易性のため _call_openai_api の差し替え（モック）を想定。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（ルックアヘッドを避けるため target_date 未満のデータのみ使用）、マクロ記事抽出、OpenAI 呼び出し、スコア合成、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API エラー時のフェイルセーフ（macro_sentiment = 0.0）やリトライ戦略を実装。

- データ処理・ETL (kabusys.data)
  - ETLResult データクラス（pipeline.ETLResult を公開）を実装し、ETL の取得件数・保存件数・品質問題・エラーを集約可能に。
  - pipeline モジュール: 差分更新、バックフィル、品質チェック（quality モジュールとの連携）等の設計方針を実装（内部ユーティリティ・テーブル存在チェック・最大日付取得等）。
  - calendar_management モジュール:
    - market_calendar テーブルを用いた営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB データ優先、未登録日の曜日ベースフォールバック、最大探索日数制限、安全性チェック、夜間バッチ calendar_update_job を実装。
  - ETL / カレンダーの J-Quants クライアント連携を想定した jquants_client 呼び出しポイントを用意（fetch/save 呼び出し部分）。

- リサーチ / 特徴量計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から EPS/ROE を取り、PER/ROE を計算（最新報告日ベース）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（例: 1,5,21 営業日）での将来リターンを一括取得。
    - calc_ic: スピアマン（ランク）で IC を計算するユーティリティ（3 銘柄以上で有効）。
    - rank: 同順位は平均ランクとするランク付け実装（丸めで ties 判定安定化）。
    - factor_summary: 基本統計量（count, mean, std, min, max, median）を計算するユーティリティ。
  - zscore_normalize は kabusys.data.stats から再利用可能に。

### 変更 (Changed)
- 設計方針・実装上の注意点を明示的に盛り込んでいる点（ドキュメント文字列内）
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない実装方針が各モジュールで採用。
  - API 呼び出しの失敗は致命的にしない（フェイルセーフ）方針を採用し、処理継続性を重視。

### 修正 (Fixed)
- 明示的なバグ修正エントリはなし（初期実装想定）。ただし DuckDB の executemany の仕様（空リスト不可）を考慮した実装や、API レスポンスの不安定さ（JSON 前後テキスト混入等）に対する回復策を実装。

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- OpenAI API キーや各種トークンの取り扱いは環境変数経由を想定。必須トークン未設定時は ValueError を投げることで明示的に失敗させる実装。

---

注記 / 実装上の設計的特徴（重要な実装判断）
- DuckDB を中心にデータを保持・クエリする設計。SQL ウィンドウ関数を多用して効率的に時系列指標を算出。
- OpenAI との連携は JSON Mode（response_format={"type": "json_object"}）を利用し、レスポンスの構造検証を厳格に行う。
- テスト容易性: OpenAI 呼び出しをラップした内部関数をモック差し替え可能にしている。
- .env の自動ロードはプロジェクトルート探索に基づき行われ、配布後の動作を考慮（__file__ から親ディレクトリを遡る）。
- 部分失敗に備え、ai_scores などテーブル更新は対象コードを絞って削除→挿入することで既存データの保護を実現。

もし実際のリリース日や追加の変更履歴（マイナー/パッチ）情報があれば、それに合わせて本CHANGELOGを更新します。
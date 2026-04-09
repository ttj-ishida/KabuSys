Keep a Changelog 準拠の CHANGELOG.md（日本語）
※コードベースの内容から推測して作成しています。

All notable changes to this project will be documented in this file.
The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

## [Unreleased]
- なし

## [0.1.0] - 2026-04-09
初回リリース。以下の主要機能およびモジュールを実装しました。

### 追加
- コア
  - パッケージ初期化 (src/kabusys/__init__.py)
    - __version__ = "0.1.0"
    - パブリックサブパッケージ: data, research, ai, execution, monitoring, strategy（__all__ の一部を公開）
- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定をロードする自動ローダーを実装
    - プロジェクトルート検出 (.git または pyproject.toml を起点)
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能
  - .env のパース機能
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの扱いに対応
  - Settings クラスを提供（settings インスタンスで使用）
    - J-Quants、kabuステーション、LINE、データベース、Paper Trading、監視しきい値、システム設定など多数のプロパティ
    - env / log_level / PAPER_FILL_MODE 等のバリデーション（許容値チェック）
    - パス系は Path 型で返却（expanduser 対応）
- AI（自然言語処理） (src/kabusys/ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI(gpt-4o-mini, JSON Mode) にバッチ送信してセンチメントを ai_scores テーブルへ書き込む
    - 時間ウィンドウ（JST基準）を計算する calc_news_window 実装
    - バッチサイズ、記事数上限、文字長上限などトークン増大対策を実装
    - レート制限・ネットワーク障害・5xx に対する指数バックオフとリトライ処理を実装
    - レスポンス検証と数値クリッピング（±1.0）
    - テスト向けに _call_openai_api をモック差替え可能
    - DuckDB 互換性のため executemany 前に空パラメータチェックを実装
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（日経225連動）200日移動平均乖離 (重み70%) とマクロニュース LLM センチメント (重み30%) を合成して日次で 'bull'/'neutral'/'bear' を判定
    - ma200_ratio の計算（target_date 未満データのみを使用、ルックアヘッドバイアス防止）
    - マクロキーワードで raw_news をフィルタし、OpenAI で macro_sentiment を評価（記事がない場合は呼ばない）
    - API エラー時はフェイルセーフで macro_sentiment=0.0 として続行
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理
    - OpenAI 呼び出しは独立実装（モジュール結合回避）でテスト容易性を確保
- データ（Data platform） (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - market_calendar を使った営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
    - DB 登録あり → DB 値優先、未登録は曜日ベースでフォールバック（整合性を保つ実装）
    - 夜間バッチ更新 job (calendar_update_job) を実装（J-Quants クライアント経由で差分取得・保存）
    - 最大探索範囲や健全性チェック（将来日付の異常検出）、バックフィル期間などを実装
  - ETL パイプライン・ユーティリティ (pipeline.py / etl.py)
    - ETLResult データクラス（取得数・保存数・品質チェック問題・エラー一覧など）
    - 差分更新、保存（idempotent）、品質チェックの設計方針（詳細ロジックは pipeline に準備）
    - etl.py で pipeline.ETLResult を再エクスポート
  - 外部依存: jquants_client、quality モジュールとの連携を想定
- 研究（Research） (src/kabusys/research)
  - factor_research.py
    - モメンタム、ボラティリティ、バリュー系のファクター計算を実装
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（データ不足時の扱い）
      - calc_volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、出来高比率
      - calc_value: raw_financials と prices_daily を組合せて PER / ROE を算出
    - DuckDB 上で SQL を主体に計算する設計（外部 API へのアクセスなし）
  - feature_exploration.py
    - calc_forward_returns: target_date から将来の終値リターンを複数ホライズンで算出（LEAD を使用）
    - calc_ic: スピアマン（ランク相関）による IC 計算（結合・None除外・最小レコードチェック）
    - rank / factor_summary: ランク計算（同順位平均）や各カラムの基本統計量を純標準ライブラリで提供
- テスト・デバッグ支援
  - OpenAI 呼び出し箇所はモック差替えが可能でユニットテストが容易
  - ロギングを各モジュールに導入（重要イベント・リトライ・例外時の警告や情報ログ）

### 設計上の注意点（ドキュメントとしての明記）
- ルックアヘッドバイアス対策
  - score_news/score_regime を含む分析系関数は datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を渡す仕様
  - DB クエリは target_date 未満や指定ウィンドウの排他条件を守る
- フェイルセーフ
  - OpenAI API 失敗時はゼロやスキップで継続する設計（例外を上位に波及させない箇所が多い）
  - DB 書き込み時はトランザクションとロールバック処理を用いて整合性を確保
- DuckDB 互換性
  - executemany に空リストを渡すと問題となるバージョンを考慮して事前チェックを実装
- セキュリティ/運用
  - 実行に必要な環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を明記・検査
  - 自動ロードされる .env / .env.local の扱い（OS 環境変数保護機能あり）
- 依存モデル・レスポンス処理
  - OpenAI モデルは gpt-4o-mini を想定、JSON Mode を利用して厳密な JSON レスポンスを期待
  - レスポンスの不整合（余計な前後テキスト等）に対する復元ロジックを実装

### 既知の制約 / 注意事項
- 一部の機能は外部モジュール（jquants_client, quality, kabu ステーション API クライアント 等）との連携を前提としており、それらの実装/設定が必要
- OpenAI API のレスポンス仕様や SDK の変更により例外処理（status_code 取り扱い等）の調整が必要になる可能性あり
- Paper Trading 用の挙動（PAPER_FILL_MODE 等）は環境変数の値検証が厳密なので設定ミスにより ValueError になる可能性あり

### 変更（Breaking changes / Deprecated / Fixed）
- なし（初回リリース）

### セキュリティ
- シークレット類（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env や CI シークレットに安全に格納してください。
- 自動 .env ロードは開発利便性向上のための機能だが、運用環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して明示的に管理することを推奨します。

---

（備考）
- 本 CHANGELOG は提供されたソースコードの内容から機能・設計意図を推測して作成しています。実際のリリースノートとして利用する場合は、人間によるレビューで文言・日付・項目の確認を行ってください。
# Changelog

全ての重要な変更は「Keep a Changelog」仕様に従って記録しています。  
このファイルは、コードベース（kabusys パッケージ）から推測して作成した初期の変更履歴です。

フォーマット:
- すべての公開リリースは日付付きで記載
- セクションは Added / Changed / Fixed / Removed / Security を基本とする

## [Unreleased]
- なし（初回リリースのみの履歴を含む）

## [0.1.0] - 2026-04-02
初回公開リリース。日本株自動売買プラットフォームのコア機能群を実装。

### Added
- パッケージ骨組みを追加
  - パッケージ名: kabusys、バージョン 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開

- 環境設定 / .env 自動読み込み
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から探索して自動ロード
  - export KEY=val 形式、シングル/ダブルクォート対応、行内コメントの扱いなどを考慮した堅牢な .env パーサを実装
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能
  - settings オブジェクトを公開し、各種必須・任意設定プロパティを提供:
    - J-Quants / kabu API / Slack トークンやチャンネル、DBパス（duckdb/sqlite）、監視閾値（CPU/メモリ/ディスク）、ログレベル、環境フラグ（development/paper_trading/live）など
  - 必須環境変数未設定時は明確な ValueError を発生

- AI モジュール（ニュース解析・市場レジーム判定）
  - news_nlp モジュール:
    - raw_news / news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ（最大20銘柄/チャンク）で送信してセンチメントを算出
    - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST（UTC変換済み）
    - 1銘柄あたりの最大記事数 / 最大文字数を制限してトークン肥大を防止
    - JSON mode を期待しつつ、JSONパース耐性（前後余計テキストの復元）を実装
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフでのリトライ
    - DuckDB 互換性のため executemany 前に空リストチェックを実施
    - ai_scores テーブルへ冪等的に書き込み（対象コードのみ DELETE → INSERT）

  - regime_detector モジュール:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、
      マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定
    - prices_daily から ma200_ratio を計算（ルックアヘッド回避: target_date 未満のデータのみ使用）
    - raw_news をマクロキーワードでフィルタして LLM に渡し macro_sentiment を評価
    - OpenAI 呼び出しは独立実装（テスト用にモック差し替え可能）
    - API失敗時は macro_sentiment=0.0 のフェイルセーフ
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）

- Research（ファクター・特徴量）モジュール
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時は None）
    - calc_volatility: 20日 ATR / 相対ATR / 20日平均売買代金 / 出来高比率を計算
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS欠損時は None）
    - DuckDB を用いた SQL + Python 実装（外部 API にアクセスしない）
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（ホライズンの検証と一括取得に最適化）
    - calc_ic: ファクター値と将来リターンのスピアマン順位相関（IC）を計算（有効レコードが3件未満なら None）
    - rank / factor_summary: ランク計算（同順位は平均ランク）と統計サマリー（count/mean/std/min/max/median）

- Data プラットフォーム
  - calendar_management:
    - JPX カレンダー管理（market_calendar）: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - market_calendar 未取得時は曜日ベースのフォールバック（土日非営業）で一貫した振る舞い
    - calendar_update_job: J-Quants API から差分取得して冪等保存、バックフィルと健全性チェックを実装
  - pipeline / etl:
    - ETLResult データクラス（取得数、保存数、品質チェック結果、エラー一覧など）
    - 差分更新、バックフィル、品質チェック、jquants_client 経由の冪等保存を想定した ETL 設計
    - jquants_client との連携を前提とした抽象化インターフェース

- テスト・可観測性を意識した設計
  - OpenAI API 呼び出しのエントリポイントをモジュールローカル関数として分離（unittest.mock.patch で置換可能）
  - ロギングを各モジュールに実装し、警告・情報ログでフェールセーフ動作を記録

### Changed
- （初回リリースのため該当なし。各モジュールに設計上の制約・挙動注記を実装）

### Fixed
- （初回リリースのため該当なしだが、以下の堅牢化を実施）
  - .env 読み込み時のファイル読み取り例外を警告に変換して処理継続
  - OpenAI レスポンスの JSON パース失敗時に例外を投げずフェイルセーフ（0.0 またはスキップ）で処理を継続
  - DuckDB executemany の空リスト問題に対する防御（空 params の場合は呼び出さない）

### Removed
- なし

### Security
- 環境変数による API キー管理を想定（OPENAI_API_KEY 等）。機密情報は .env に置かず安全な方法で管理することを推奨。

---

注記（設計上のポイント、コードからの推測）:
- すべての分析 / スコアリング処理はルックアヘッドバイアスを避ける設計（datetime.today() や date.today() を直接参照しない、target_date ベースでウィンドウ計算）になっています。
- API 呼び出しに対してはリトライ／バックオフ／フォールバックが実装されており、外部依存の不安定さを考慮した堅牢な実装方針が取られています。
- DuckDB に対する互換性配慮（date 型取り扱い、executemany 空配列回避、ROW_NUMBER 等）を行っています。

今後のリリース案（推奨）
- バージョン 0.2.x: strategy / execution / monitoring モジュールの実装（実際の発注ロジック、監視・アラート連携、Slack 通知）
- バージョン 0.3.x: テストカバレッジ拡充、CI/CD、ドキュメント（API / データスキーマ）、性能改善（ETL 並列化など）

もし特定モジュールごとにより細かい変更履歴（例: 関数レベルの変更点や既知の制限）をご希望でしたら、そのモジュールを指定してください。コードの別ファイルや追加コミットがあれば、それに基づいて差分ベースの CHANGELOG を作成します。
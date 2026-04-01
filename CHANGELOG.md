# Changelog

すべての重要な変更をこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠します。  
バージョン番号は PEP440 に準拠します。

なお本 CHANGELOG は提示されたソースコードから機能・設計意図を推測して作成しています。

## [Unreleased]
- 開発中の変更点はここに記載します。

## [0.1.0] - 2026-04-01
初回リリース（推定）。日本株自動売買システムのコアライブラリを公開。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン: 0.1.0）。
  - __all__ で主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定・環境読み込み (kabusys.config)
  - .env / .env.local と OS 環境変数を組み合わせた自動環境変数読み込み機能を実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準に探索（CWD 非依存）。
    - .env のパースは export プレフィックス・クォート・エスケープ・インラインコメント等に対応。
    - 読み込み優先順: OS 環境 > .env.local (> 上書き) > .env（ただし OS 環境は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - Settings クラスで設定をプロパティとして公開（型変換・検証付き）。
    - J-Quants、kabuステーション、Slack、DB パス、監視閾値、実行環境（development / paper_trading / live）などを含む。
    - 必須環境変数未設定時は明示的な ValueError を送出。
    - ログレベルや環境名のバリデーションを実装。

- AI（自然言語処理）機能 (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）でニュースセンチメント（-1.0〜1.0）を銘柄ごとに評価。
    - バッチ処理（最大 20 銘柄/回）、トークン肥大化対策（記事数・文字数制限）、JSON Mode 利用。
    - リトライ（429/ネットワーク/5xx/タイムアウト）を実装（指数バックオフ）。非リトライ例外はスキップして継続。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、コード照合、数値チェック）。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）で部分失敗時の既存データ保護。
    - lookahead バイアス防止のため日付取得に datetime.today()/date.today() を直接参照しない設計。
  - regime_detector.score_regime
    - ETF（1321）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースはキーワードフィルタで抽出し OpenAI（gpt-4o-mini）により macro_sentiment を取得。
    - API 障害時は macro_sentiment を 0.0 にフォールバックし処理を継続（フェイルセーフ）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行う。
    - テストしやすいように OpenAI 呼び出し部を差し替え可能（モックポイントを用意）。

- Research（リサーチ）モジュール (kabusys.research)
  - factor_research
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR）、Value（PER、ROE）等のファクター計算関数を提供。
    - DuckDB SQL を主体に、営業日ベースの窓や不足データ時の None 処理を実装。
  - feature_exploration
    - calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関）、rank（同順位平均ランク）、factor_summary（基本統計量）を提供。
    - 外部依存を持たず標準ライブラリのみで実装。

- Data（データプラットフォーム）モジュール (kabusys.data)
  - calendar_management
    - JPX マーケットカレンダーの管理・照会ユーティリティ。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar 未取得時は曜日ベースでフォールバック（週末は非営業日）。
    - calendar_update_job で J-Quants から差分取得 → 保存（バックフィル、健全性チェック付き）。
  - pipeline / etl
    - ETLResult データクラスを公開（ETL 実行の統計・品質問題・エラーを集約）。
    - pipeline モジュールは差分取得、保存（idempotent）、品質チェックのフロー設計を意図。

- 共通
  - DuckDB を主要データ層として利用する設計。SQL + Python の組み合わせで大量データを効率的に集計・計算。
  - ロギングを各モジュールに導入し、情報・警告・例外情報を適切に出力。
  - DB トランザクション（BEGIN/COMMIT/ROLLBACK）で整合性を確保。
  - テストしやすさを考慮した設計（OpenAI 呼び出しのモックポイント、環境読み込みの無効化フラグ等）。

### 変更 (Changed)
- 初版リリースのため履歴なし。

### 修正 (Fixed)
- 初版リリースのため履歴なし。

### 既知の問題 (Known issues)
- 一部ソースが途中で切れている/未完成の可能性
  - 提供された pipeline モジュールの末尾で _get_max_date の戻り処理が途切れている（"return date.fro" のような断片が見受けられる）。実運用前にソース全体の整合性（構文エラー・未定義参照）確認が必要です。
- 外部依存・運用準備
  - OpenAI API（OPENAI_API_KEY）、J-Quants 関連（JQUANTS_REFRESH_TOKEN）、kabuステーション（KABU_API_PASSWORD）、Slack（SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）などの環境変数が必須。Settings は未設定時に例外を出すため、環境準備が必須。
- API コスト・レート制限
  - news_nlp/regime_detector は外部の LLM 呼び出しを行うため、利用には API コストやレート制限の管理が必要。

### セキュリティ (Security)
- 初版リリースのため特記事項なし。ただし実運用時は機密情報（API キー等）の管理・保護、.env ファイル取り扱いに注意。

---

作業メモ（開発者向け）
- ユニットテスト・統合テストを通じて以下を確認すること：
  - .env パーサーのクォート・エスケープ・コメント処理の境界ケース。
  - OpenAI 呼び出しの各種例外ハンドリング（429 / ネットワーク断 / タイムアウト / 5xx）。
  - DuckDB に対する executemany の空リスト制約（既に考慮済みだがバージョン差異の確認）。
  - calendar_update_job の健全性チェック・バックフィル挙動。
  - pipeline モジュールの未完成箇所の修正。

問い合わせ・貢献方法についてはリポジトリの README を参照してください。
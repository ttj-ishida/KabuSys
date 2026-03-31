# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠してバージョン管理を行います。  
セマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31

初回公開リリース。

### 追加 (Added)
- パッケージ初期構成を追加
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パブリック API のエントリポイントを定義 (src/kabusys/__init__.py): data, strategy, execution, monitoring を公開。

- 環境設定・読み込み機能 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を読み込む自動ローダーを実装。読み込み順序は OS 環境変数 > .env.local > .env。
  - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探す実装で、CWD に依存しない挙動。
  - .env 行パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート内エスケープやインラインコメントの扱いに対応。
  - 上書き制御 (override) と OS 環境変数を保護する protected 設定に対応。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - 必須設定取得ヘルパー _require と Settings クラスを提供（J-Quants、kabuステーション、Slack、データベースパスなどのプロパティを定義）。
  - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL）と is_live/is_paper/is_dev のユーティリティを提供。

- AI 関連モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング (news_nlp.py)
    - raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini) の JSON Mode を利用して銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む処理を提供。
    - バッチ処理（1回あたり最大20銘柄）、記事トリム（最大記事数・最大文字数）、レスポンス検証、スコアクリップ、エクスポネンシャルバックオフによるリトライを実装。
    - API キー注入（引数 or OPENAI_API_KEY）と、テスト容易性のための OpenAI 呼び出し差し替えポイントを用意。
    - ルックアヘッドバイアス回避のため日時参照を外部化（target_date ベースで動作）。

  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - DuckDB の prices_daily/raw_news を参照して ma200_ratio とマクロ記事を取得し、OpenAI を呼び出して macro_sentiment を算出。最終的に market_regime テーブルへ冪等書き込み。
    - エラー時のフェイルセーフ（API失敗時は macro_sentiment=0.0）、再試行・バックオフ、レスポンスパース保護を実装。
    - 内部で datetime.today() を直接参照しない設計。（ルックアヘッドバイアス対策）

  - AI モジュールでの共通設計:
    - OpenAI 呼び出しはモジュールごとに独立実装し、テスト時に差し替え可能。
    - JSON モードレスポンスの厳密なバリデーション処理を採用。

- データプラットフォーム（src/kabusys/data）
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開（pipeline.ETLResult を etl.py で再エクスポート）。
    - 差分取得、バックフィル、品質チェック統合の設計概略とユーティリティ関数（テーブル存在確認、最大日付取得など）を実装。
    - ETL 実行結果の辞書化(to_dict)で品質問題リストを直列化。

  - マーケットカレンダー管理 (calendar_management.py)
    - JPX カレンダーを管理する market_calendar テーブルに対する判定・検索・更新ユーティリティを提供。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day などの API を実装。
    - DB 登録がない場合の曜日フォールバック、最大探索日数制限、バックフィル、健全性チェック、J-Quants からの差分取得ジョブ (calendar_update_job) を実装。
    - データの有無や NULL を考慮した堅牢な挙動を実装。

- リサーチ機能（src/kabusys/research）
  - ファクター計算 (factor_research.py)
    - Momentum（1M/3M/6M リターン, 200日MA乖離）、Volatility（20日 ATR / ATR比 / 平均売買代金 / 出来高比率）、Value（PER、ROE）を DuckDB の prices_daily / raw_financials から計算。
    - データ不足時の扱い（None）、DuckDB ウィンドウ関数を活用した実装。

  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（複数ホライズン対応）、IC（Spearman 相関）計算、ランク付けユーティリティ、ファクター統計サマリーを実装。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で動作するよう設計。
    - rank 実装は同順位の平均ランクを返す（丸め誤差対策あり）。

- その他ユーティリティ
  - data パッケージのパブリック再エクスポート(s) の基盤を追加（pipeline.ETLResult の公開など）。

### 変更 (Changed)
- N/A（初回リリースのため過去からの変更はなし）

### 削除 (Removed)
- N/A

### 修正 (Fixed)
- N/A（初回リリース）

### 非推奨 (Deprecated)
- N/A

### セキュリティ (Security)
- 環境設定ローダーは既存 OS 環境変数を保護する protected 機構を導入し、.env による不意な上書きを制御可能。
- OpenAI API キーの取り扱いは引数注入または環境変数に限定し、未設定時は明確な ValueError を発生させる安全設計。

### 注意・設計上の重要ポイント（リリースノート）
- ルックアヘッドバイアス防止のため、多くの分析関数は内部で date.today() / datetime.today() を直接参照せず、外部から与えられる target_date に基づいて計算します。運用・テスト時は target_date を明示的に指定してください。
- OpenAI 呼び出しはネットワーク問題・レート制限・5xx 等に対してリトライとフォールバック（スコア 0.0 やスキップ）を行い、処理の継続性を重視しています。運用時は API キーのレートとコストに注意してください。
- DuckDB との組み合わせで executemany に空リストを渡すと互換性の問題が出るバージョンがあるため、空パラメータは事前チェックしてから実行する実装になっています。
- .env のパースは POSIX シェル風の簡易実装ですが、極端な複雑なケースは未カバーの可能性があります。必要に応じて環境値の検証を行ってください。

---

脚注: 実装の説明はソースコードのコメント・実装から推測して記載しています。実運用前に設定項目（環境変数）、DB スキーマ（テーブル名・列）、および外部 API クレデンシャルを必ず確認してください。
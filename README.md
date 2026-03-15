# KabuSys

KabuSysは日本株の自動売買システムの骨組み（スケルトン）です。  
このリポジトリは、データ取得・売買戦略・注文実行・モニタリングといった自動売買に必要な主要コンポーネントをモジュール単位で分離して提供します。現状はフレームワーク／テンプレートとしての提供で、実際のアルゴリズムやAPI接続は各モジュール内で実装していく想定です。

バージョン: 0.1.0

---

## 主要コンセプト・目的
- 自動売買システムを構築するためのモジュール構成（data, strategy, execution, monitoring）を提供
- 各モジュールを容易に拡張できる設計を想定
- 実装者は各モジュールに実際のデータソースや注文API、戦略を実装して利用する

---

## 機能一覧（現状）
- パッケージ化されたモジュール構成
  - data: 市場データ取得・加工を想定
  - strategy: 売買判断ロジックを想定
  - execution: 注文送信・注文管理を想定
  - monitoring: ログ・稼働監視・通知を想定
- パッケージメタ情報（バージョン等）

注意: 現在のリポジトリは最小構成のスケルトンで、各機能は具体的な実装を行う必要があります。

---

## セットアップ手順

前提
- Python 3.8 以上（任意の最新安定版でも可）
- Git

1. リポジトリをクローン
```bash
git clone <このリポジトリのURL>
cd <リポジトリ名>
```

2. 仮想環境を作成（推奨）
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

3. インストール（開発中は編集反映が容易なeditableインストール推奨）
```bash
pip install -e .
```
注意: このリポジトリに `setup.py` / `pyproject.toml` がない場合は、手動でパスを通すか、ルートから直接実行することができます。実際の運用では依存ライブラリ（APIクライアント、pandas、numpy など）を `requirements.txt` や `pyproject.toml` に追加してください。

---

## 使い方（例とガイド）

このパッケージはモジュール構成を提供します。実装例（疑似コード）を示します。

基本のインポートとバージョン確認:
```python
import kabusys

print(kabusys.__version__)  # 例: "0.1.0"

from kabusys import data, strategy, execution, monitoring
```

各モジュールは以下の責務を想定しています（例）:

- data
  - 市場データを取得（ティッカー、板情報、約定履歴、OHLCなど）
  - データの前処理、指標計算
- strategy
  - データを受け取り、買い/売り/待機などのシグナルを生成
  - ポジション管理のロジックを持つ
- execution
  - 取引所またはブローカーAPIと通信して注文を発行・取消・照会
  - レート制限やエラー処理を扱う
- monitoring
  - ログ出力、アラート（メール/Slack等）、可視化や稼働監視

簡単な擬似ワークフロー:
```python
# 1. データ取得
price = data.get_latest_price("7203")  # 実装は利用者にて

# 2. シグナル生成
sig = strategy.generate_signal(price)  # 実装は利用者にて

# 3. 注文実行
if sig == "BUY":
    execution.place_order(symbol="7203", side="BUY", qty=100)

# 4. モニタリング
monitoring.log_event("注文を発行しました", {"symbol": "7203", "signal": sig})
```

注意: 上記の関数（get_latest_price / generate_signal / place_order / log_event）はサンプルであり、実際には各モジュール内に具体的な関数・クラスを実装してください。

拡張のヒント:
- data モジュール: 銘柄情報やAPIキーは外部設定ファイル（ENV, YAML, TOML）で管理する
- strategy モジュール: Strategy ベースクラス（抽象クラス）を作り、複数戦略を派生して実装する
- execution モジュール: 再試行戦略や注文状態の永続化（DB）を導入する
- monitoring モジュール: メトリクスをPrometheusへ出す、エラートリガーでSlack/メール通知など

---

## ディレクトリ構成

現在の最小構成を示します。

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py          # パッケージ初期化（__version__ 定義）
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
```

ファイルの説明:
- src/kabusys/__init__.py
  - パッケージ名とバージョン情報を定義しています（__version__ = "0.1.0"）。
  - __all__ は外部に公開するサブモジュール名を列挙しています: ["data", "strategy", "execution", "monitoring"]
- src/kabusys/*/__init__.py
  - 各サブモジュールのエントリポイント。ここにモジュール内の公開APIを実装していきます。

---

## 開発・貢献
- 問題報告（Issue）や機能提案はIssueで受け付けてください。
- プルリクエストは歓迎します。コードスタイル、テスト、ドキュメントを含めてください。
- 実運用で使用する場合は必ずテスト環境で十分な検証を行ってください（特に注文実行部分）。

---

## ライセンス
このリポジトリにライセンスファイルが付属していない場合は、利用前にライセンス方針を明確にしてください。テンプレートとして利用する場合は適切なライセンス（MIT, Apache 2.0 など）を追加することを推奨します。

---

このREADMEは骨組みを説明するためのものです。実際の自動売買システムを構築する際は、データ精度、APIの信頼性、エラーハンドリング、リスク管理、法令順守（金融商品取引法等）に十分配慮してください。
# KabuSys

KabuSys は日本株の自動売買システムのためのシンプルな基盤（スターターキット）です。モジュールを分離しており、データ取得、売買戦略、注文実行、監視をそれぞれ独立して実装・拡張できます。

現在のバージョン: 0.1.0

---

## 概要

このプロジェクトは自動売買システムを構築するための骨組み（フレームワーク）を提供します。以下の責務を持つ4つの主要パッケージを含みます。

- data: 市場データの取得・前処理を担当
- strategy: 売買戦略の実装を担当
- execution: 注文送信や約定管理を担当
- monitoring: ログ、メトリクス、アラートなどの監視を担当

現在はモジュールの初期構成（パッケージの雛形）のみが含まれており、各モジュールはプロジェクト要件に合わせて拡張して使います。

---

## 機能一覧（現時点）

- パッケージ構成（data / strategy / execution / monitoring）を提供
- バージョン情報（kabusys.__version__ = "0.1.0"）
- 拡張ポイントの明確化（各パッケージを独立して実装可能）

（注）実際のデータ取得や注文送信の実装は含まれていません。API クライアントや取引ロジックは追加で実装してください。

---

## 要件

- Python 3.8 以上（推奨：3.9+）
- git（コード取得時）

プロジェクト固有の外部ライブラリはこのリポジトリに含まれていません。利用する API クライアントや数値計算ライブラリ（pandas、numpy 等）は必要に応じて追加してください。

---

## セットアップ手順

1. リポジトリをクローンする

   ```
   git clone <リポジトリのURL>
   cd <リポジトリ名>
   ```

2. 仮想環境を作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール

   現状は必須の requirements ファイルがないため、開発中はプロジェクトルートでソースを import できるようにします。パッケージ配布用の設定がある場合は以下のように編集してください。

   - 開発時にソースを editable install する例（プロジェクトに setup.py / pyproject.toml がある前提）:

     ```
     pip install -e .
     ```

   - もしくは簡易的に PYTHONPATH を設定して直接参照する方法:

     ```
     export PYTHONPATH=$(pwd)/src:${PYTHONPATH}   # macOS / Linux
     set PYTHONPATH=%cd%\src;%PYTHONPATH%         # Windows (PowerShell / cmd に応じて調整)
     ```

4. 必要なライブラリ（例）

   実装に応じて以下を追加でインストールしてください（例）:

   ```
   pip install pandas numpy requests
   ```

---

## 使い方（基本）

パッケージをインストールまたは PYTHONPATH を設定したら次のように利用できます。

- バージョン確認の例：

```python
import kabusys
print(kabusys.__version__)  # "0.1.0"
```

- 各モジュールの雛形を拡張して使う例（概念例）：

```python
# data フォルダに market_data.py を作って関数を実装する
from kabusys.data import market_data

df = market_data.fetch_ohlcv("7203")  # 例: トヨタのコード
# データ前処理
df = market_data.preprocess(df)

# strategy に戦略クラスを実装する
from kabusys.strategy import my_strategy

signal = my_strategy.compute_signal(df)

# execution で注文を送る
from kabusys.execution import broker

if signal == "BUY":
    broker.send_order(symbol="7203", side="BUY", qty=100)
```

注意: 上記はサンプルの概念コードです。実際には API キー管理、リトライや例外処理、約定確認などの実装が必要です。

---

## ディレクトリ構成

現在のソースツリー（主要ファイルのみ）:

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py            # パッケージのメタ情報（バージョン等）
│     ├─ data/
│     │  └─ __init__.py         # データ取得・加工用モジュールを配置
│     ├─ strategy/
│     │  └─ __init__.py         # 戦略ロジックを配置
│     ├─ execution/
│     │  └─ __init__.py         # 注文実行・ブローカー連携を配置
│     └─ monitoring/
│        └─ __init__.py         # ログ・モニタリング関連を配置
```

将来的に追加することが想定されるファイル例:

- src/kabusys/data/market_data.py
- src/kabusys/strategy/base.py
- src/kabusys/strategy/sample_strategy.py
- src/kabusys/execution/broker.py
- src/kabusys/monitoring/logger.py
- tests/ （ユニットテスト）

---

## 拡張と実装ガイド（簡潔）

- data: 外部 API（取引所 API、ブローカー API、CSV/DB）からデータを取得するクラス・関数を実装。キャッシュ・バックテスト用データの整形もここで行う。
- strategy: 戦略は入力データ（OHLCV など）を受け取り、売買シグナルを返す純粋関数またはステートフルなクラスとして設計する。
- execution: 注文の送信、注文管理（キャンセル・約定確認）、ポジション管理、API キーや認証情報の安全な管理を実装する。
- monitoring: ログ出力（ファイル/標準出力）、メトリクス収集、アラート（メール/Slack）などを提供する。

---

## 注意点

- 実際の売買を行う際は、必ずテスト/サンドボックス環境で十分な検証を行ってください。
- 金融商品取引に関わる法的・規制上の要件を確認してください。本リポジトリは教育用/開発用のフレームワークであり、実運用に関する保証はありません。

---

## 連絡・貢献

バグ報告や機能改善の提案は Issue を立ててください。プルリクエスト歓迎します。貢献時は既存のコーディングスタイルに合わせてください。

---

以上。必要があれば、README に含めるサンプル実装（簡単な戦略やデータ取得の雛形）を追加で作成します。どの部分を優先して実装したいか教えてください。